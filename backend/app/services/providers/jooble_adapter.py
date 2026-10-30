import time
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import httpx

from app.core.config import settings
from app.services.providers.base_provider import BaseProvider, NormalizedJob, NormalizedCompany


class JoobleAdapter(BaseProvider):
    def __init__(self, api_key: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.api_key = api_key or settings.JOOBLE_API_KEY
        self.daily_request_cap = settings.DISCOVERY_DAILY_QUOTA_JOOBLE

    @property
    def provider_name(self) -> str:
        return "jooble"

    @property
    def display_name(self) -> str:
        return "Jooble Job Aggregator"

    @property
    def tier(self) -> int:
        return 2

    @property
    def free_tier_info(self) -> str:
        return "Jooble Partner Sandbox (500-request lifetime evaluation limit; disabled by default under permanent zero-cost policy)"

    def is_configured(self) -> bool:
        if not getattr(settings, "ENABLE_EVALUATION_PROVIDERS", False):
            return False
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

        url = f"https://jooble.org/api/{self.api_key}"
        payload = {
            "keywords": query if not remote_only else f"{query} remote",
            "location": location or "India",
            "page": 1
        }

        start_time = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=settings.DISCOVERY_TIMEOUT_SECONDS) as client:
                res = await client.post(url, json=payload)
                latency = (time.perf_counter() - start_time) * 1000

                if res.status_code == 200:
                    data = res.json()
                    job_list = data.get("jobs", [])
                    self.record_query_success(latency, len(job_list))
                elif res.status_code in {401, 403}:
                    self._last_error = "Invalid Jooble API key."
                    self.record_query_error(self._last_error, is_auth_error=True)
                    return []
                elif res.status_code == 429:
                    self._last_error = "Jooble API rate limit reached."
                    self.record_query_error(self._last_error, is_rate_limit=True, cooldown_seconds=settings.DISCOVERY_RATE_LIMIT_COOLDOWN_SECONDS)
                    return []
                else:
                    self._last_error = f"Jooble status {res.status_code}"
                    self.record_query_error(self._last_error)
                    return []
        except Exception as e:
            self._last_error = f"Jooble error: {str(e)}"
            self.record_query_error(self._last_error)
            return []

        jobs: List[NormalizedJob] = []

        for item in job_list[:limit]:
            title = item.get("title", "").strip()
            company = item.get("company", "").strip() or "Hiring Employer"
            link = item.get("link", "").strip()
            if not title or not link:
                continue

            snippet = item.get("snippet", "")
            is_remote = "remote" in (title + " " + snippet).lower() or remote_only

            jobs.append(NormalizedJob(
                title=title,
                company_name=company,
                description=snippet[:500] if snippet else None,
                location=item.get("location") or location,
                is_remote=is_remote,
                work_arrangement="remote" if is_remote else "hybrid",
                employment_type=item.get("type", "full-time").lower(),
                primary_url=link,
                source_name=item.get("source", "Jooble"),
                source_provider="jooble",
                posting_date=item.get("updated"),
                extracted_skills=[],
                evidence_excerpt=snippet[:250] if snippet else None,
                confidence=0.88
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
