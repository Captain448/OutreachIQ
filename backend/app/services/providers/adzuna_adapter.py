import time
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import httpx

from app.core.config import settings
from app.services.providers.base_provider import BaseProvider, NormalizedJob, NormalizedCompany


class AdzunaAdapter(BaseProvider):
    def __init__(self, app_id: Optional[str] = None, app_key: Optional[str] = None):
        self.app_id = app_id or settings.ADZUNA_APP_ID
        self.app_key = app_key or settings.ADZUNA_APP_KEY
        self.endpoint = "https://api.adzuna.com/v1/api/jobs/in/search/1"
        self._last_latency_ms: Optional[float] = None
        self._last_error: Optional[str] = None
        self._results_returned = 0
        self._last_queried: Optional[datetime] = None

    @property
    def provider_name(self) -> str:
        return "adzuna"

    @property
    def display_name(self) -> str:
        return "Adzuna Structured Jobs"

    def is_configured(self) -> bool:
        return bool(self.app_id and self.app_key and len(self.app_key.strip()) > 5)

    async def search_jobs(
        self,
        query: str,
        location: Optional[str] = None,
        remote_only: bool = False,
        limit: int = 15
    ) -> List[NormalizedJob]:
        if not self.is_configured():
            return []

        params = {
            "app_id": self.app_id,
            "app_key": self.app_key,
            "what": query,
            "where": location or "India",
            "results_per_page": min(limit, 20),
            "content-type": "application/json"
        }

        start_time = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=settings.DISCOVERY_TIMEOUT_SECONDS) as client:
                res = await client.get(self.endpoint, params=params)
                self._last_latency_ms = (time.perf_counter() - start_time) * 1000
                self._last_queried = datetime.now(timezone.utc)

                if res.status_code == 200:
                    self._last_error = None
                    data = res.json()
                elif res.status_code in {401, 403}:
                    self._last_error = "Invalid Adzuna app credentials."
                    return []
                elif res.status_code == 429:
                    self._last_error = "Adzuna API rate limit reached."
                    return []
                else:
                    self._last_error = f"Adzuna status {res.status_code}"
                    return []
        except Exception as e:
            self._last_error = f"Adzuna network error: {str(e)}"
            return []

        results = data.get("results", [])
        self._results_returned += len(results)
        jobs: List[NormalizedJob] = []

        for item in results[:limit]:
            title = item.get("title", "").strip()
            company_obj = item.get("company", {})
            company_name = company_obj.get("display_name", "").strip() or "Hiring Employer"
            url = item.get("redirect_url", "").strip()
            if not title or not url:
                continue

            desc = item.get("description", "")
            lower_desc = (title + " " + desc).lower()
            is_remote = "remote" in lower_desc or remote_only

            jobs.append(NormalizedJob(
                title=title,
                company_name=company_name,
                description=desc[:500] if desc else None,
                location=item.get("location", {}).get("display_name") or location,
                is_remote=is_remote,
                work_arrangement="remote" if is_remote else "hybrid",
                employment_type="full-time",
                primary_url=url,
                source_name="Adzuna",
                source_provider="adzuna",
                posting_date=item.get("created"),
                extracted_skills=[],
                evidence_excerpt=desc[:250] if desc else None,
                confidence=0.90
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
        return []

    def get_health_status(self) -> Dict[str, Any]:
        return {
            "provider_name": self.provider_name,
            "display_name": self.display_name,
            "is_configured": self.is_configured(),
            "status": "active" if self.is_configured() and not self._last_error else ("disabled" if not self.is_configured() else "error"),
            "error_message": self._last_error,
            "latency_ms": self._last_latency_ms,
            "results_returned": self._results_returned,
            "quota_limit_info": "Adzuna Developer Portal Tier",
            "last_queried": self._last_queried
        }
