import time
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import httpx

from app.core.config import settings
from app.services.providers.base_provider import BaseProvider, NormalizedJob, NormalizedCompany


class SerpApiAdapter(BaseProvider):
    def __init__(self, api_key: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.api_key = api_key or settings.SERPAPI_API_KEY
        self.endpoint = "https://serpapi.com/search.json"
        self.daily_request_cap = settings.DISCOVERY_DAILY_QUOTA_SERPAPI

    @property
    def provider_name(self) -> str:
        return "serpapi"

    @property
    def display_name(self) -> str:
        return "SerpApi (Google Jobs)"

    @property
    def tier(self) -> int:
        return 2

    @property
    def free_tier_info(self) -> str:
        return "SerpApi Free Plan (100 searches/mo, 10/day safe limit)"

    def is_configured(self) -> bool:
        return bool(self.api_key and len(self.api_key.strip()) > 5)

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

        search_query = query
        if location:
            search_query += f" {location}"
        if remote_only:
            search_query += " remote"

        params = {
            "engine": "google_jobs",
            "q": search_query,
            "api_key": self.api_key,
            "hl": "en"
        }

        start_time = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=settings.DISCOVERY_TIMEOUT_SECONDS) as client:
                res = await client.get(self.endpoint, params=params)
                latency = (time.perf_counter() - start_time) * 1000

                if res.status_code == 200:
                    data = res.json()
                    jobs_results = data.get("jobs_results", [])
                    self.record_query_success(latency, len(jobs_results))
                elif res.status_code in {401, 403}:
                    self._last_error = "Invalid SerpApi key."
                    self.record_query_error(self._last_error, is_auth_error=True)
                    return []
                elif res.status_code == 429:
                    self._last_error = "SerpApi monthly search credits exhausted."
                    self.record_query_error(self._last_error, is_rate_limit=True, cooldown_seconds=settings.DISCOVERY_RATE_LIMIT_COOLDOWN_SECONDS)
                    return []
                else:
                    self._last_error = f"SerpApi returned status {res.status_code}"
                    self.record_query_error(self._last_error)
                    return []
        except Exception as e:
            self._last_error = f"SerpApi network error: {str(e)}"
            self.record_query_error(self._last_error)
            return []

        jobs: List[NormalizedJob] = []

        for item in jobs_results[:limit]:
            title = item.get("title", "").strip()
            company = item.get("company_name", "").strip()
            if not title or not company:
                continue

            # Extract apply links
            apply_options = item.get("apply_options", [])
            primary_url = apply_options[0].get("link") if apply_options else item.get("share_link") or "https://google.com"

            desc = item.get("description", "")
            exts = item.get("detected_extensions", {})
            is_remote = bool(exts.get("work_from_home", False)) or remote_only

            jobs.append(NormalizedJob(
                title=title,
                company_name=company,
                description=desc[:500] if desc else None,
                location=item.get("location") or location,
                is_remote=is_remote,
                work_arrangement="remote" if is_remote else "hybrid",
                employment_type=exts.get("schedule_type", "full-time").lower(),
                primary_url=primary_url,
                source_name=item.get("via", "Google Jobs"),
                source_provider="serpapi",
                posting_date=exts.get("posted_at"),
                extracted_skills=[],
                evidence_excerpt=desc[:250] if desc else None,
                confidence=0.95
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
        return super().get_health_status()
