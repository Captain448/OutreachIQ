import time
import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import httpx

from app.core.config import settings
from app.services.providers.base_provider import BaseProvider, NormalizedJob, NormalizedCompany


class JSearchAdapter(BaseProvider):
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.JSEARCH_API_KEY
        self.endpoint = "https://jsearch.p.rapidapi.com/search"
        self._last_latency_ms: Optional[float] = None
        self._last_error: Optional[str] = None
        self._results_returned = 0
        self._last_queried: Optional[datetime] = None

    @property
    def provider_name(self) -> str:
        return "jsearch"

    @property
    def display_name(self) -> str:
        return "JSearch (Aggregated Job Feeds)"

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

        search_query = f"{query} in {location}" if location else f"{query} in India"
        if remote_only:
            search_query += " remote"

        headers = {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
        }
        params = {
            "query": search_query,
            "page": "1",
            "num_pages": "1"
        }

        start_time = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=settings.DISCOVERY_TIMEOUT_SECONDS) as client:
                res = await client.get(self.endpoint, headers=headers, params=params)
                self._last_latency_ms = (time.perf_counter() - start_time) * 1000
                self._last_queried = datetime.now(timezone.utc)

                if res.status_code == 200:
                    self._last_error = None
                    data = res.json()
                elif res.status_code == 429:
                    self._last_error = "JSearch RapidAPI quota limit reached."
                    return []
                else:
                    self._last_error = f"JSearch error status {res.status_code}"
                    return []
        except Exception as e:
            self._last_error = f"JSearch request error: {str(e)}"
            return []

        data_list = data.get("data", [])
        self._results_returned += len(data_list)
        jobs: List[NormalizedJob] = []

        for item in data_list[:limit]:
            title = item.get("job_title", "").strip()
            company = item.get("employer_name", "").strip()
            url = item.get("job_apply_link", "") or item.get("job_google_link", "")
            if not title or not company or not url:
                continue

            desc = item.get("job_description", "")
            is_remote = bool(item.get("job_is_remote", False)) or remote_only

            # Extract required skills listed by JSearch highlights
            highlights = item.get("job_highlights", {})
            qualifications = highlights.get("Qualifications", [])

            jobs.append(NormalizedJob(
                title=title,
                company_name=company,
                description=desc[:500] if desc else None,
                location=item.get("job_city") or item.get("job_country") or location,
                is_remote=is_remote,
                work_arrangement="remote" if is_remote else "hybrid",
                employment_type=item.get("job_employment_type", "FULLTIME").lower(),
                primary_url=url,
                source_name=item.get("job_publisher", "JSearch Aggregate"),
                source_provider="jsearch",
                posting_date=item.get("job_posted_at_datetime_utc"),
                extracted_skills=qualifications[:8],
                evidence_excerpt=desc[:250] if desc else None,
                confidence=0.92
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
        # JSearch is specialized for job openings; does not perform direct company research
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
            "quota_limit_info": "RapidAPI JSearch Quota",
            "last_queried": self._last_queried
        }
