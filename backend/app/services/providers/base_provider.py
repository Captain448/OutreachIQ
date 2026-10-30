import abc
import os
import json
import threading
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any, Tuple
from pydantic import BaseModel, Field


class NormalizedJob(BaseModel):
    title: str
    company_name: str
    description: Optional[str] = None
    location: Optional[str] = None
    is_remote: bool = False
    work_arrangement: str = "flexible"
    employment_type: str = "full-time"
    primary_url: str
    application_url: Optional[str] = None
    salary_range: Optional[str] = None
    source_name: str
    source_provider: str
    source_category: str = "Job Board"
    posting_date: Optional[str] = None
    extracted_skills: List[str] = Field(default_factory=list)
    evidence_excerpt: Optional[str] = None
    confidence: float = 1.0
    extraction_quality: float = 1.0
    company_confidence: float = 1.0
    verification_status: str = "LISTING_FOUND_STATUS_UNVERIFIED"
    verification_details: Dict[str, Any] = Field(default_factory=dict)
    is_verified: bool = False
    last_verified_at: Optional[str] = None
    rejection_reason: Optional[str] = None


class CompanySignalItem(BaseModel):
    signal_type: str        # e.g., "tech_stack", "product_launch", "funding_expansion", "hiring_need"
    headline: str
    date: Optional[str] = None
    evidence_url: Optional[str] = None
    excerpt: Optional[str] = None
    confidence: float = 1.0


class NormalizedCompany(BaseModel):
    name: str
    domain: Optional[str] = None
    website_url: Optional[str] = None
    description: Optional[str] = None
    industry: Optional[str] = None
    headquarters: Optional[str] = None
    signals: List[CompanySignalItem] = Field(default_factory=list)
    source_name: str
    source_provider: str
    source_url: str
    evidence_excerpt: Optional[str] = None
    confidence: float = 1.0


class PersistentQuotaTracker:
    """
    Lightweight, persistent local ledger for daily provider quota counters.
    Ensures counters survive backend reboots and remain synchronized across
    multiple uvicorn worker processes without requiring paid external infrastructure.
    """
    _lock = threading.Lock()

    @classmethod
    def _get_storage_path(cls) -> str:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        data_dir = os.path.join(base_dir, "data")
        os.makedirs(data_dir, exist_ok=True)
        return os.path.join(data_dir, "provider_quotas.json")

    @classmethod
    def get_usage(cls, provider_name: str, date_str: Optional[str] = None) -> int:
        if date_str is None:
            date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        path = cls._get_storage_path()
        if not os.path.exists(path):
            return 0
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return int(data.get(date_str, {}).get(provider_name, 0))
        except Exception:
            return 0

    @classmethod
    def increment_usage(cls, provider_name: str, date_str: Optional[str] = None, amount: int = 1) -> int:
        if date_str is None:
            date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        path = cls._get_storage_path()
        with cls._lock:
            data: Dict[str, Any] = {}
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                except Exception:
                    data = {}

            # Prune ledger entries older than 7 days to keep disk footprint minimal
            cutoff_date = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")
            data = {k: v for k, v in data.items() if k >= cutoff_date}

            if date_str not in data:
                data[date_str] = {}
            current = data[date_str].get(provider_name, 0)
            new_val = current + amount
            data[date_str][provider_name] = new_val

            temp_path = f"{path}.tmp"
            try:
                with open(temp_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
                os.replace(temp_path, path)
            except Exception:
                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except Exception:
                        pass
            return new_val

    @classmethod
    def set_usage(cls, provider_name: str, usage: int, date_str: Optional[str] = None) -> None:
        if date_str is None:
            date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        path = cls._get_storage_path()
        with cls._lock:
            data: Dict[str, Any] = {}
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                except Exception:
                    data = {}
            if date_str not in data:
                data[date_str] = {}
            data[date_str][provider_name] = usage
            temp_path = f"{path}.tmp"
            try:
                with open(temp_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
                os.replace(temp_path, path)
            except Exception:
                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except Exception:
                        pass

    @classmethod
    def reset_usage_for_test(cls, provider_name: Optional[str] = None, date_str: Optional[str] = None) -> None:
        if date_str is None:
            date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        path = cls._get_storage_path()
        with cls._lock:
            if not os.path.exists(path):
                return
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if date_str in data:
                    if provider_name:
                        data[date_str].pop(provider_name, None)
                    else:
                        data.pop(date_str, None)
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
            except Exception:
                pass


class BaseProvider(abc.ABC):
    def __init__(self, persist_quota: bool = True):
        self.persist_quota: bool = persist_quota
        self.daily_requests_used: int = 0
        self.daily_request_cap: int = 50
        self.last_quota_reset_date: Optional[str] = None
        self.rate_limit_cooldown_until: Optional[datetime] = None
        self.consecutive_errors: int = 0
        self.circuit_status: str = "active"
        self._last_latency_ms: Optional[float] = None
        self._last_error: Optional[str] = None
        self._results_returned: int = 0
        self._last_queried: Optional[datetime] = None
        self._check_and_reset_daily_quota()

    @property
    @abc.abstractmethod
    def provider_name(self) -> str:
        """Machine identifier (e.g. 'tavily', 'exa', 'jsearch')"""
        pass

    @property
    @abc.abstractmethod
    def display_name(self) -> str:
        """Human-readable display name"""
        pass

    @property
    def tier(self) -> int:
        """Provider tier: 1 for Primary, 2 for Backup"""
        return 1 if self.provider_name in {"tavily", "exa"} else 2

    @property
    def free_tier_info(self) -> str:
        """Documented free-tier quota & usage limits"""
        return "Developer Free Tier"

    def _check_and_reset_daily_quota(self) -> None:
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if self.persist_quota:
            persisted_used = PersistentQuotaTracker.get_usage(self.provider_name, today_str)
            self.daily_requests_used = max(self.daily_requests_used, persisted_used)

        if self.last_quota_reset_date != today_str:
            if self.persist_quota:
                self.daily_requests_used = PersistentQuotaTracker.get_usage(self.provider_name, today_str)
            else:
                self.daily_requests_used = 0
            self.last_quota_reset_date = today_str
            if self.circuit_status == "quota_exhausted":
                self.circuit_status = "active"
                self._last_error = None

    def can_query(self) -> Tuple[bool, Optional[str]]:
        """
        Determines whether the provider is eligible to receive queries based on:
        1. Configuration state (valid API keys/credentials present)
        2. Daily free quota safety cap (synchronized with persistent multi-worker ledger)
        3. Active rate-limit / circuit breaker cooldown
        """
        self._check_and_reset_daily_quota()

        if self.persist_quota:
            today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            self.daily_requests_used = max(
                self.daily_requests_used,
                PersistentQuotaTracker.get_usage(self.provider_name, today_str)
            )

        if not self.is_configured():
            return False, f"Provider '{self.provider_name}' has missing credentials or is unconfigured."

        if self.circuit_status == "disabled_auth_error":
            return False, f"Provider '{self.provider_name}' disabled due to previous 401/403 authentication error."

        now = datetime.now(timezone.utc)
        if self.rate_limit_cooldown_until and now < self.rate_limit_cooldown_until:
            wait_sec = int((self.rate_limit_cooldown_until - now).total_seconds())
            return False, f"Provider '{self.provider_name}' is rate-limited (cooldown remaining: {wait_sec}s)."

        if self.daily_requests_used >= self.daily_request_cap:
            self.circuit_status = "quota_exhausted"
            return False, f"Provider '{self.provider_name}' reached daily free quota cap ({self.daily_requests_used}/{self.daily_request_cap})."

        return True, None

    def record_query_success(self, latency_ms: float, results_count: int) -> None:
        if self.persist_quota:
            today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            self.daily_requests_used = PersistentQuotaTracker.increment_usage(self.provider_name, today_str, 1)
        else:
            self.daily_requests_used += 1

        self._results_returned += results_count
        self._last_latency_ms = latency_ms
        self._last_queried = datetime.now(timezone.utc)
        self._last_error = None
        self.consecutive_errors = 0
        self.circuit_status = "active"

    def record_query_error(
        self,
        error_msg: str,
        is_auth_error: bool = False,
        is_rate_limit: bool = False,
        cooldown_seconds: int = 60
    ) -> None:
        self._last_error = error_msg
        self._last_queried = datetime.now(timezone.utc)
        self.consecutive_errors += 1

        if is_auth_error:
            # Fatal authentication error - disable immediately without endless retries
            self.circuit_status = "disabled_auth_error"
        elif is_rate_limit:
            self.circuit_status = "rate_limited"
            self.rate_limit_cooldown_until = datetime.now(timezone.utc) + timedelta(seconds=cooldown_seconds)
        else:
            self.circuit_status = "error"

    def record_quota_exhausted(self, reason: str = "Free tier quota exhausted") -> None:
        self._last_error = reason
        self.circuit_status = "quota_exhausted"
        self.daily_requests_used = self.daily_request_cap
        if self.persist_quota:
            today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            PersistentQuotaTracker.set_usage(self.provider_name, self.daily_request_cap, today_str)

    @abc.abstractmethod
    def is_configured(self) -> bool:
        """Returns True if required API keys / credentials are set"""
        pass

    @abc.abstractmethod
    async def search_jobs(
        self,
        query: str,
        location: Optional[str] = None,
        remote_only: bool = False,
        limit: int = 20
    ) -> List[NormalizedJob]:
        """Discover advertised job openings"""
        pass

    @abc.abstractmethod
    async def search_companies(
        self,
        skills: List[str],
        industries: List[str],
        roles: List[str],
        locations: Optional[List[str]] = None,
        limit: int = 10
    ) -> List[NormalizedCompany]:
        """Discover potential company targets with public signals"""
        pass

    def get_health_status(self) -> Dict[str, Any]:
        """Returns provider availability, latency, error count, and quota status"""
        self._check_and_reset_daily_quota()
        now = datetime.now(timezone.utc)
        cooldown_rem = None
        if self.rate_limit_cooldown_until and now < self.rate_limit_cooldown_until:
            cooldown_rem = int((self.rate_limit_cooldown_until - now).total_seconds())

        if not self.is_configured():
            status = "disabled"
            err = self._last_error or f"Credentials not configured in environment for {self.display_name}."
        elif self.circuit_status != "active":
            status = self.circuit_status
            err = self._last_error
        elif self._last_error:
            status = "error"
            err = self._last_error
        else:
            status = "active"
            err = None

        return {
            "provider_name": self.provider_name,
            "display_name": self.display_name,
            "is_configured": self.is_configured(),
            "tier": self.tier,
            "status": status,
            "circuit_status": self.circuit_status,
            "daily_requests_used": self.daily_requests_used,
            "daily_request_cap": self.daily_request_cap,
            "free_tier_info": self.free_tier_info,
            "cooldown_remaining_seconds": cooldown_rem,
            "error_message": err,
            "latency_ms": self._last_latency_ms,
            "results_returned": self._results_returned,
            "quota_limit_info": self.free_tier_info,
            "last_queried": self._last_queried,
        }
