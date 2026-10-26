import time
import re
import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import httpx

from app.core.config import settings
from app.services.providers.base_provider import BaseProvider, NormalizedJob, NormalizedCompany, CompanySignalItem
from app.services.providers.tavily_adapter import COMMON_SKILLS


class ExaAdapter(BaseProvider):
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.EXA_API_KEY
        self.endpoint = "https://api.exa.ai/search"
        self._last_latency_ms: Optional[float] = None
        self._last_error: Optional[str] = None
        self._results_returned = 0
        self._last_queried: Optional[datetime] = None

    @property
    def provider_name(self) -> str:
        return "exa"

    @property
    def display_name(self) -> str:
        return "Exa Semantic Search"

    def is_configured(self) -> bool:
        return bool(self.api_key and len(self.api_key.strip()) > 5)

    async def _post_exa(self, query: str, num_results: int = 10, search_type: str = "neural") -> Dict[str, Any]:
        if not self.is_configured():
            raise ValueError("Exa API key is not configured.")

        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        }

        payload = {
            "query": query,
            "type": search_type,
            "numResults": min(num_results, 25),
            "useAutoprompt": True,
            "contents": {
                "text": {
                    "maxCharacters": 600
                },
                "highlights": {
                    "numSentences": 2
                }
            }
        }

        retries = settings.DISCOVERY_MAX_RETRIES
        delay = 1.0

        for attempt in range(retries + 1):
            start_time = time.perf_counter()
            try:
                async with httpx.AsyncClient(timeout=settings.DISCOVERY_TIMEOUT_SECONDS) as client:
                    response = await client.post(self.endpoint, headers=headers, json=payload)
                    self._last_latency_ms = (time.perf_counter() - start_time) * 1000
                    self._last_queried = datetime.now(timezone.utc)

                    if response.status_code == 200:
                        self._last_error = None
                        return response.json()
                    elif response.status_code == 401:
                        self._last_error = "Invalid Exa API key provided."
                        raise ValueError(self._last_error)
                    elif response.status_code == 429:
                        self._last_error = "Exa rate limit or monthly credit quota exhausted."
                        raise ValueError(self._last_error)
                    elif response.status_code >= 500:
                        if attempt < retries:
                            await asyncio.sleep(delay)
                            delay *= 2
                            continue
                        self._last_error = f"Exa server error HTTP {response.status_code}"
                        raise RuntimeError(self._last_error)
                    else:
                        self._last_error = f"Exa API returned status {response.status_code}: {response.text[:200]}"
                        raise RuntimeError(self._last_error)
            except httpx.TimeoutException:
                if attempt < retries:
                    await asyncio.sleep(delay)
                    delay *= 2
                    continue
                self._last_error = "Exa request timed out."
                raise TimeoutError(self._last_error)
            except httpx.RequestError as e:
                self._last_error = f"Exa network communication error: {str(e)}"
                raise RuntimeError(self._last_error)

        raise RuntimeError(self._last_error or "Exa request failed after retries.")

    async def search_jobs(
        self,
        query: str,
        location: Optional[str] = None,
        remote_only: bool = False,
        limit: int = 15,
        skills: Optional[List[str]] = None,
        target_roles: Optional[List[str]] = None,
        experience_level: Optional[str] = None
    ) -> List[NormalizedJob]:
        if not self.is_configured():
            return []

        loc_str = location or "India or Remote"
        remote_str = "remote" if remote_only else ""
        skills_str = (" " + " ".join(skills[:2])) if skills else ""
        semantic_query = f"Open job listing and application for a {query}{skills_str} {remote_str} in {loc_str}:"

        try:
            data = await self._post_exa(semantic_query, num_results=min(limit * 2, 20), search_type="neural")
        except Exception as e:
            self._last_error = str(e)
            return []

        results = data.get("results", [])
        self._results_returned += len(results)

        from app.services.listing_extractor import ListingExtractor

        extraction_tasks = []
        for item in results:
            raw_title = item.get("title", "").strip()
            url = item.get("url", "").strip()
            text_body = item.get("text", "").strip()
            highlights = " ".join(item.get("highlights", []))
            combined_text = (text_body + " " + highlights).strip()

            if not raw_title or not url:
                continue

            extraction_tasks.append(
                ListingExtractor.extract_from_candidate(
                    url=url,
                    title_hint=raw_title,
                    snippet_hint=combined_text,
                    source_provider="exa",
                    source_category="Semantic Job Search",
                    confidence_hint=float(item.get("score", 0.90)) if item.get("score") is not None else 0.90
                )
            )

        if not extraction_tasks:
            return []

        extracted = await asyncio.gather(*extraction_tasks, return_exceptions=True)
        jobs: List[NormalizedJob] = []
        seen_urls = set()

        for res in extracted:
            if isinstance(res, tuple):
                is_valid, job, reason = res
                if is_valid and job and job.primary_url not in seen_urls:
                    seen_urls.add(job.primary_url)
                    jobs.append(job)
                    if len(jobs) >= limit:
                        break

        return jobs

    async def search_companies(
        self,
        skills: List[str],
        industries: List[str],
        roles: List[str],
        locations: Optional[List[str]] = None,
        limit: int = 10
    ) -> List[NormalizedCompany]:
        if not self.is_configured():
            return []

        skills_str = ", ".join(skills[:4]) if skills else "software engineering"
        role_str = roles[0] if roles else "technology"
        loc_str = locations[0] if locations else "India"

        # Semantic query for companies actively developing products with these specific technical competencies
        semantic_query = f"Innovative technology companies and startups in {loc_str} building products using {skills_str} and hiring {role_str}:"

        try:
            data = await self._post_exa(semantic_query, num_results=limit, search_type="neural")
        except Exception as e:
            self._last_error = str(e)
            return []

        results = data.get("results", [])
        self._results_returned += len(results)
        companies: List[NormalizedCompany] = []

        for item in results:
            raw_title = item.get("title", "").strip()
            url = item.get("url", "").strip()
            text_body = item.get("text", "").strip()
            highlights = " ".join(item.get("highlights", []))
            combined_text = (text_body + " " + highlights).strip()

            if not raw_title or not url:
                continue

            company_name = self._extract_company_name(raw_title, url)
            if company_name.lower() in {"github", "medium", "wikipedia", "youtube", "twitter", "x"}:
                continue

            domain = self._extract_domain(url)
            
            signal = CompanySignalItem(
                signal_type="product_and_technology_alignment",
                headline=raw_title,
                date=item.get("publishedDate"),
                evidence_url=url,
                excerpt=highlights[:280] if highlights else text_body[:280],
                confidence=float(item.get("score", 0.88))
            )

            companies.append(NormalizedCompany(
                name=company_name,
                domain=domain,
                website_url=f"https://{domain}" if domain else url,
                description=combined_text[:400] if combined_text else "Semantically matched technology company.",
                industry=industries[0] if industries else "Software / AI",
                headquarters=locations[0] if locations else "India",
                signals=[signal],
                source_name="Exa Semantic Discovery",
                source_provider="exa",
                source_url=url,
                evidence_excerpt=highlights[:280] if highlights else text_body[:280],
                confidence=float(item.get("score", 0.88))
            ))

        return companies

    def get_health_status(self) -> Dict[str, Any]:
        if not self.is_configured():
            status = "disabled"
            err = "API key not configured in environment (EXA_API_KEY)"
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
            "status": status,
            "error_message": err,
            "latency_ms": self._last_latency_ms,
            "results_returned": self._results_returned,
            "quota_limit_info": "Standard Exa Neural Search Tier",
            "last_queried": self._last_queried
        }

    @staticmethod
    def _extract_company_name(title: str, url: str) -> str:
        for sep in [" at ", " - ", " | "]:
            if sep in title:
                parts = title.split(sep)
                if len(parts) >= 2:
                    p0, p1 = parts[0].strip(), parts[1].strip()
                    if sep == " at ":
                        candidate = p1
                    elif any(role_word in p0.lower() for role_word in ["engineer", "developer", "architect", "manager", "lead", "scientist", "intern"]):
                        candidate = p1
                    else:
                        candidate = p0
                    if not any(portal in candidate.lower() for portal in ["linkedin", "indeed", "naukri", "internshala"]):
                        return " ".join(candidate.split()[0:3])

        if ": " in title:
            parts = title.split(": ")
            p0 = parts[0].strip()
            if not any(role_word in p0.lower() for role_word in ["engineer", "developer", "architect", "lead"]):
                return " ".join(p0.split()[0:3])

        domain = ExaAdapter._extract_domain(url)
        if domain:
            ignored_subdomains = {"www", "jobs", "careers", "blog", "app", "work", "apply"}
            tld_set = {"com", "org", "net", "io", "ai", "co", "in", "works", "tech", "dev"}
            parts = [p for p in domain.split(".") if p.lower() not in ignored_subdomains and p.lower() not in tld_set]
            if parts:
                return parts[0].capitalize()
            base = domain.split(".")[0].capitalize()
            if base.lower() not in ignored_subdomains:
                return base
        return "Unknown Organization"

    @staticmethod
    def _clean_job_title(title: str, company: str) -> str:
        clean = title
        if company and company.lower() in clean.lower():
            clean = re.sub(re.escape(company), "", clean, flags=re.IGNORECASE)
        for sep in [" - ", " | ", " at ", ": "]:
            if sep in clean:
                parts = clean.split(sep)
                for part in parts:
                    if any(rw in part.lower() for rw in ["engineer", "developer", "architect", "lead", "scientist", "intern"]):
                        return part.strip()
        return clean.strip(" -|:") or title

    @staticmethod
    def _extract_domain(url: str) -> Optional[str]:
        match = re.search(r"https?://(?:www\.)?([^/]+)", url)
        return match.group(1) if match else None

    @staticmethod
    def _identify_source(url: str) -> str:
        lower = url.lower()
        if "linkedin.com" in lower:
            return "LinkedIn (Public Search)"
        elif "naukri.com" in lower:
            return "Naukri"
        elif "internshala.com" in lower:
            return "Internshala"
        elif "unstop.com" in lower:
            return "Unstop"
        elif "wellfound.com" in lower:
            return "Wellfound"
        return "Company Career Page"
