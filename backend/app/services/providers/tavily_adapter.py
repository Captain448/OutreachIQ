import time
import re
import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import httpx

from app.core.config import settings
from app.services.providers.base_provider import BaseProvider, NormalizedJob, NormalizedCompany, CompanySignalItem
from app.services.discovery_query_builder import DiscoveryQueryBuilder

# Curated reference skill keywords for extracting recognized competencies from job snippets
COMMON_SKILLS = {
    "python", "javascript", "typescript", "fastapi", "django", "flask", "react", "angular", "vue",
    "node.js", "docker", "kubernetes", "aws", "gcp", "azure", "postgresql", "mysql", "mongodb",
    "redis", "pytorch", "tensorflow", "machine learning", "nlp", "llm", "langchain", "langgraph", "git", "ci/cd"
}


class TavilyAdapter(BaseProvider):
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.TAVILY_API_KEY
        self.endpoint = "https://api.tavily.com/search"
        self._last_latency_ms: Optional[float] = None
        self._last_error: Optional[str] = None
        self._results_returned = 0
        self._last_queried: Optional[datetime] = None

    @property
    def provider_name(self) -> str:
        return "tavily"

    @property
    def display_name(self) -> str:
        return "Tavily Web Search"

    def is_configured(self) -> bool:
        return bool(self.api_key and len(self.api_key.strip()) > 5)

    async def _post_tavily(self, query: str, max_results: int = 10, search_depth: str = "basic") -> Dict[str, Any]:
        if not self.is_configured():
            raise ValueError("Tavily API key is not configured.")

        payload = {
            "api_key": self.api_key,
            "query": query,
            "search_depth": search_depth,
            "include_answer": False,
            "max_results": min(max_results, 20)
        }

        retries = settings.DISCOVERY_MAX_RETRIES
        delay = 1.0

        for attempt in range(retries + 1):
            start_time = time.perf_counter()
            try:
                async with httpx.AsyncClient(timeout=settings.DISCOVERY_TIMEOUT_SECONDS) as client:
                    response = await client.post(self.endpoint, json=payload)
                    self._last_latency_ms = (time.perf_counter() - start_time) * 1000
                    self._last_queried = datetime.now(timezone.utc)

                    if response.status_code == 200:
                        self._last_error = None
                        return response.json()
                    elif response.status_code == 401:
                        self._last_error = "Invalid Tavily API key provided."
                        raise ValueError(self._last_error)
                    elif response.status_code == 429:
                        self._last_error = "Tavily rate limit or search quota exhausted."
                        raise ValueError(self._last_error)
                    elif response.status_code >= 500:
                        if attempt < retries:
                            await asyncio.sleep(delay)
                            delay *= 2
                            continue
                        self._last_error = f"Tavily server error HTTP {response.status_code}"
                        raise RuntimeError(self._last_error)
                    else:
                        self._last_error = f"Tavily API returned status {response.status_code}: {response.text[:200]}"
                        raise RuntimeError(self._last_error)
            except httpx.TimeoutException:
                if attempt < retries:
                    await asyncio.sleep(delay)
                    delay *= 2
                    continue
                self._last_error = "Tavily request timed out."
                raise TimeoutError(self._last_error)
            except httpx.RequestError as e:
                self._last_error = f"Tavily network error: {str(e)}"
                raise RuntimeError(self._last_error)

        raise RuntimeError(self._last_error or "Tavily request failed after retries.")

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

        remote_pref = "remote" if remote_only else "flexible"
        roles_list = target_roles or ([query] if query else ["Software Engineer"])
        target_skills = skills or []

        # Generate targeted queries across ATS portals, LinkedIn, and Regional boards
        planned_queries = DiscoveryQueryBuilder.build_targeted_queries(
            target_roles=roles_list,
            skills=target_skills,
            locations=[location] if location else ["India"],
            remote_preference=remote_pref,
            experience_level=experience_level or "mid",
            limit_queries=2
        )

        candidate_items: List[Tuple[Dict[str, Any], str, str]] = []
        for q_entry in planned_queries[:2]:
            q_text = q_entry["query"]
            cat = q_entry.get("source_category", "Job Board")
            src_key = q_entry.get("source_key", "tavily")
            try:
                data = await self._post_tavily(q_text, max_results=max(5, limit // 2))
                for res in data.get("results", []):
                    candidate_items.append((res, cat, src_key))
            except Exception as e:
                self._last_error = str(e)

        # Fallback if planned queries yielded nothing
        if not candidate_items:
            loc_clause = f"({location})" if location else "(India OR Remote)"
            rem_clause = "Remote" if remote_only else ""
            fallback_q = f'"{query}" {rem_clause} {loc_clause} job hiring site:linkedin.com/jobs OR site:naukri.com OR site:greenhouse.io'
            try:
                data = await self._post_tavily(fallback_q.strip(), max_results=limit)
                for res in data.get("results", []):
                    candidate_items.append((res, "Job Board", "fallback"))
            except Exception as e:
                self._last_error = str(e)

        self._results_returned += len(candidate_items)

        from app.services.listing_extractor import ListingExtractor

        # Concurrently extract and verify listings
        extraction_tasks = []
        for item, cat, _ in candidate_items[:limit * 2]:
            raw_title = item.get("title", "").strip()
            url = item.get("url", "").strip()
            content = item.get("content", "").strip()
            if not raw_title or not url:
                continue
            extraction_tasks.append(
                ListingExtractor.extract_from_candidate(
                    url=url,
                    title_hint=raw_title,
                    snippet_hint=content,
                    source_provider="tavily",
                    source_category=cat,
                    confidence_hint=float(item.get("score", 0.85)) if item.get("score") is not None else 0.85
                )
            )

        if not extraction_tasks:
            return []

        results = await asyncio.gather(*extraction_tasks, return_exceptions=True)
        jobs: List[NormalizedJob] = []
        seen_urls = set()

        for res in results:
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

        skills_str = " ".join(skills[:3]) if skills else "engineering"
        industry_str = " ".join(industries[:2]) if industries else "technology"
        loc_str = locations[0] if locations else "India"

        # Search for company launches, technical initiatives, and expansion announcements
        query = f"startups {industry_str} {skills_str} {loc_str} (launch OR engineering OR funding OR expansion OR product)"
        
        try:
            data = await self._post_tavily(query, max_results=limit)
        except Exception as e:
            self._last_error = str(e)
            return []

        results = data.get("results", [])
        self._results_returned += len(results)
        companies: List[NormalizedCompany] = []

        for item in results:
            raw_title = item.get("title", "").strip()
            url = item.get("url", "").strip()
            content = item.get("content", "").strip()
            if not raw_title or not url:
                continue

            company_name = self._extract_company_name(raw_title, url)
            if company_name.lower() in {"linkedin", "naukri", "internshala", "google", "medium", "github"}:
                continue

            domain = self._extract_domain(url)
            
            signal = CompanySignalItem(
                signal_type="product_or_tech_expansion",
                headline=raw_title,
                date=None,
                evidence_url=url,
                excerpt=content[:250] if content else None,
                confidence=float(item.get("score", 0.80))
            )

            companies.append(NormalizedCompany(
                name=company_name,
                domain=domain,
                website_url=f"https://{domain}" if domain else url,
                description=content[:350] if content else "Discovered via public engineering & product announcements.",
                industry=industries[0] if industries else "Technology",
                headquarters=locations[0] if locations else "India",
                signals=[signal],
                source_name="Tavily Web Intelligence",
                source_provider="tavily",
                source_url=url,
                evidence_excerpt=content[:250] if content else None,
                confidence=float(item.get("score", 0.80))
            ))

        return companies

    def get_health_status(self) -> Dict[str, Any]:
        if not self.is_configured():
            status = "disabled"
            err = "API key not configured in environment (TAVILY_API_KEY)"
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
            "quota_limit_info": "Standard Tavily Search Tier",
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

        domain = TavilyAdapter._extract_domain(url)
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
        for sep in [" at ", " - ", " | ", ": "]:
            if sep in clean:
                clean = clean.split(sep)[0].strip()
        return clean or title

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
        elif "wellfound.com" in lower or "angel.co" in lower:
            return "Wellfound"
        elif "indeed.com" in lower:
            return "Indeed"
        return "Company Career Page"
