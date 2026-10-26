import time
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import httpx

from app.core.config import settings
from app.services.providers.base_provider import BaseProvider, NormalizedJob, NormalizedCompany


class JoobleAdapter(BaseProvider):
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.JOOBLE_API_KEY
        self._last_latency_ms: Optional[float] = None
        self._last_error: Optional[str] = None
        self._results_returned = 0
        self._last_queried: Optional[datetime] = None

    @property
    def provider_name(self) -> str:
        return "jooble"

    @property
    def display_name(self) -> str:
        return "Jooble Job Aggregator"

    def is_configured(self) -> bool:
        return bool(self.api_key and len(self.api_key.strip()) > 5)

    async def search_jobs(
        self,
        query: str,
        location: Optional[str] = None,
        remote_only: bool = False,
        limit: int = 15
    ) -> List[NormalizedJob]:
        if not self.is_configured():
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
                self._last_latency_ms = (time.perf_counter() - start_time) * 1000
                self._last_queried = datetime.now(timezone.utc)

                if res.status_code == 200:
                    self._last_error = None
                    data = res.json()
                elif res.status_code in {401, 403}:
                    self._last_error = "Invalid Jooble API key."
                    return []
                elif res.status_code == 429:
                    self._last_error = "Jooble API rate limit reached."
                    return []
                else:
                    self._last_error = f"Jooble status {res.status_code}"
                    return []
        except Exception as e:
            self._last_error = f"Jooble error: {str(e)}"
            return []

        job_list = data.get("jobs", [])
        self._results_returned += len(job_list)
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
        return {
            "provider_name": self.provider_name,
            "display_name": self.display_name,
            "is_configured": self.is_configured(),
            "status": "active" if self.is_configured() and not self._last_error else ("disabled" if not self.is_configured() else "error"),
            "error_message": self._last_error,
            "latency_ms": self._last_latency_ms,
            "results_returned": self._results_returned,
            "quota_limit_info": "Jooble API Standard Tier",
            "last_queried": self._last_queried
        }
