import time
import re
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import httpx

from app.core.config import settings
from app.services.providers.base_provider import BaseProvider, NormalizedJob, NormalizedCompany, CompanySignalItem
from app.services.providers.tavily_adapter import COMMON_SKILLS


class RemotiveAdapter(BaseProvider):
    """
    Public Developer Feed Adapter using Remotive's official, permitted free public API.
    Does not require any API keys, paid subscriptions, or billing accounts.
    Serves as an authoritative zero-cost fallback for remote software opportunities.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.endpoint = "https://remotive.com/api/remote-jobs"
        self.daily_request_cap = settings.DISCOVERY_DAILY_QUOTA_REMOTIVE

    @property
    def provider_name(self) -> str:
        return "remotive"

    @property
    def display_name(self) -> str:
        return "Remotive Public Remote Feed"

    @property
    def tier(self) -> int:
        return 2

    @property
    def free_tier_info(self) -> str:
        return "Permanent Free Public Feed (No API Key Required)"

    def is_configured(self) -> bool:
        # Public feed requires no secret credentials - permanently configured
        return True

    async def search_jobs(
        self,
        query: str,
        location: Optional[str] = None,
        remote_only: bool = False,
        limit: int = 15,
        **kwargs
    ) -> List[NormalizedJob]:
        can_run, reason = self.can_query()
        if not can_run:
            self._last_error = reason
            return []

        search_term = query.strip()
        params = {
            "category": "software-dev",
            "search": search_term,
            "limit": min(limit, 20)
        }

        start_time = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=settings.DISCOVERY_TIMEOUT_SECONDS) as client:
                res = await client.get(self.endpoint, params=params)
                latency = (time.perf_counter() - start_time) * 1000

                if res.status_code == 200:
                    data = res.json()
                    raw_jobs = data.get("jobs", [])
                    self.record_query_success(latency, len(raw_jobs))
                elif res.status_code == 429:
                    err = "Remotive public API rate limit reached. Pausing for cooldown."
                    self.record_query_error(err, is_rate_limit=True, cooldown_seconds=settings.DISCOVERY_RATE_LIMIT_COOLDOWN_SECONDS)
                    return []
                else:
                    err = f"Remotive API returned status {res.status_code}"
                    self.record_query_error(err)
                    return []
        except httpx.TimeoutException:
            err = "Remotive public API request timed out."
            self.record_query_error(err)
            return []
        except Exception as e:
            err = f"Remotive public API communication error: {str(e)}"
            self.record_query_error(err)
            return []

        jobs: List[NormalizedJob] = []
        for item in raw_jobs[:limit]:
            title = (item.get("title") or "").strip()
            company_name = (item.get("company_name") or "").strip() or "Hiring Organization"
            url = (item.get("url") or "").strip()
            if not title or not url:
                continue

            raw_desc = item.get("description") or ""
            # Strip HTML tags from description if present
            clean_desc = re.sub(r"<[^>]+>", " ", raw_desc)
            clean_desc = " ".join(clean_desc.split())

            cand_loc = (item.get("candidate_required_location") or "Remote").strip()
            tags = item.get("tags") or []
            extracted = [t.title() for t in tags if t.lower() in COMMON_SKILLS]

            # Text skill extraction if tags list is sparse
            if len(extracted) < 2:
                lower_body = (title + " " + clean_desc).lower()
                for s in COMMON_SKILLS:
                    if re.search(r"\b" + re.escape(s) + r"\b", lower_body):
                        cap = s.title()
                        if cap not in extracted:
                            extracted.append(cap)

            job_type = (item.get("job_type") or "full_time").lower().replace("_", "-")
            salary = item.get("salary") or None

            jobs.append(NormalizedJob(
                title=title,
                company_name=company_name,
                description=clean_desc[:600] if clean_desc else None,
                location=cand_loc,
                is_remote=True,
                work_arrangement="remote",
                employment_type=job_type,
                primary_url=url,
                salary_range=salary,
                source_name="Remotive Public Job Feed",
                source_provider="remotive",
                source_category="Public Feed",
                posting_date=item.get("publication_date"),
                extracted_skills=extracted,
                evidence_excerpt=clean_desc[:250] if clean_desc else None,
                confidence=0.92,
                extraction_quality=0.95,
                verification_status="LISTING_FOUND_STATUS_UNVERIFIED",
                is_verified=False
            ))

        return jobs

    async def search_companies(
        self,
        skills: List[str],
        industries: List[str],
        roles: List[str],
        locations: Optional[List[str]] = None,
        limit: int = 10
    ) -> List[NormalizedCompany]:
        # Public job feed discovers companies strictly via verified job postings
        return []

    def get_health_status(self) -> Dict[str, Any]:
        can_run, reason = self.can_query()
        if not can_run:
            status = self.circuit_status
            err = reason
        elif self._last_error:
            status = "error"
            err = self._last_error
        else:
            status = "active"
            err = None

        cooldown_remaining = None
        if self.rate_limit_cooldown_until:
            diff = (self.rate_limit_cooldown_until - datetime.now(timezone.utc)).total_seconds()
            if diff > 0:
                cooldown_remaining = int(diff)

        return {
            "provider_name": self.provider_name,
            "display_name": self.display_name,
            "is_configured": True,
            "status": status,
            "tier": self.tier,
            "circuit_status": self.circuit_status,
            "error_message": err,
            "latency_ms": self._last_latency_ms,
            "results_returned": self._results_returned,
            "daily_requests_used": self.daily_requests_used,
            "daily_request_cap": self.daily_request_cap,
            "quota_limit_info": self.free_tier_info,
            "cooldown_remaining_seconds": cooldown_remaining,
            "last_queried": self._last_queried
        }
