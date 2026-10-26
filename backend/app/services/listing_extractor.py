import re
import json
import logging
from typing import Dict, Any, Optional, Tuple, List
from urllib.parse import urlparse
import httpx
from bs4 import BeautifulSoup

from app.services.providers.base_provider import NormalizedJob
from app.services.opportunity_normalizer import OpportunityNormalizer, AGGREGATOR_NAMES, KNOWN_LOCATIONS
from app.services.listing_verification_service import ListingVerificationService, JobVerificationStatus

logger = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36 OutReachIQ-Verification/1.0"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


class ListingExtractor:
    @staticmethod
    async def fetch_page_content(url: str, timeout_seconds: float = 8.0) -> Optional[str]:
        """
        Retrieves accessible page content asynchronously with safe redirect handling and timeouts.
        Returns HTML text if successful, or None if inaccessible/blocked.
        """
        try:
            async with httpx.AsyncClient(
                headers=DEFAULT_HEADERS,
                timeout=timeout_seconds,
                follow_redirects=True,
                verify=False
            ) as client:
                resp = await client.get(url)
                if resp.status_code == 200 and "text/html" in resp.headers.get("content-type", ""):
                    return resp.text
        except Exception as e:
            logger.debug(f"Direct page retrieval failed for {url}: {e}")
        return None

    @classmethod
    async def extract_from_candidate(
        cls,
        url: str,
        title_hint: Optional[str] = None,
        snippet_hint: Optional[str] = None,
        source_provider: str = "web_search",
        source_category: str = "Job Board",
        confidence_hint: Optional[float] = None
    ) -> Tuple[bool, Optional[NormalizedJob], Optional[str]]:
        """
        Extracts an individual job listing from candidate URL or hints.
        1. Validates against aggressive directory/search fragment patterns.
        2. Attempts structured JobPosting metadata extraction if page is accessible.
        3. Falls back to HTML and snippet parsing.
        4. Returns (is_valid, job_or_none, rejection_reason).
        """
        raw_title = title_hint or ""
        
        # 1. Immediate Pre-filter Quality Gate on Candidate Hints
        is_valid_candidate, reject_reason = OpportunityNormalizer.validate_job_listing(
            title=raw_title,
            company_name="Candidate Employer",  # placeholder for pre-gate
            primary_url=url,
            description=snippet_hint
        )
        # Check title directory patterns specifically
        if not is_valid_candidate and ("pagination" in (reject_reason or "") or "directory" in (reject_reason or "")):
            return False, None, reject_reason

        # 2. Try fetching full HTML page content
        html_content = await cls.fetch_page_content(url)

        # 3. If HTML available, attempt JSON-LD extraction
        if html_content:
            job_from_ld = cls._extract_from_json_ld(html_content, url, source_provider, source_category)
            if job_from_ld:
                # Validate the extracted title and employer
                is_valid, reason = OpportunityNormalizer.validate_job_listing(
                    title=job_from_ld.title,
                    company_name=job_from_ld.company_name,
                    primary_url=url,
                    description=job_from_ld.description
                )
                if is_valid:
                    verification_res = ListingVerificationService.verify_html_content(
                        content=html_content,
                        url=url,
                        expected_title=job_from_ld.title,
                        expected_company=job_from_ld.company_name
                    )
                    if verification_res["status"] == JobVerificationStatus.EXPIRED_OR_CLOSED.value:
                        return False, None, f"Position expired or closed: {verification_res.get('details')}"
                    if verification_res["status"] == JobVerificationStatus.INVALID_OR_REJECTED.value:
                        return False, None, f"Invalid listing: {verification_res.get('details')}"

                    if confidence_hint is not None:
                        job_from_ld.confidence = confidence_hint
                    job_from_ld.verification_status = verification_res["status"]
                    job_from_ld.is_verified = verification_res["is_verified"]
                    job_from_ld.verification_details = verification_res
                    job_from_ld.last_verified_at = verification_res.get("verified_at")
                    job_from_ld.extraction_quality = 0.95
                    return True, job_from_ld, None

            # Fallback to HTML tag parsing (OpenGraph / Heading)
            job_from_html = cls._extract_from_html_tags(html_content, url, source_provider, source_category, snippet_hint)
            if job_from_html:
                is_valid, reason = OpportunityNormalizer.validate_job_listing(
                    title=job_from_html.title,
                    company_name=job_from_html.company_name,
                    primary_url=url,
                    description=job_from_html.description
                )
                if is_valid:
                    verification_res = ListingVerificationService.verify_html_content(
                        content=html_content,
                        url=url,
                        expected_title=job_from_html.title,
                        expected_company=job_from_html.company_name
                    )
                    if verification_res["status"] == JobVerificationStatus.EXPIRED_OR_CLOSED.value:
                        return False, None, f"Position expired or closed: {verification_res.get('details')}"
                    if verification_res["status"] == JobVerificationStatus.INVALID_OR_REJECTED.value:
                        return False, None, f"Invalid listing: {verification_res.get('details')}"

                    if confidence_hint is not None:
                        job_from_html.confidence = confidence_hint
                    job_from_html.verification_status = verification_res["status"]
                    job_from_html.is_verified = verification_res["is_verified"]
                    job_from_html.verification_details = verification_res
                    job_from_html.last_verified_at = verification_res.get("verified_at")
                    job_from_html.extraction_quality = 0.85
                    return True, job_from_html, None

        # 4. Fallback to Snippet & URL Extraction
        if raw_title and snippet_hint:
            company_name = OpportunityNormalizer.clean_employer_name(
                company_name=raw_title.split(" - ")[-1] if " - " in raw_title else "Direct Employer",
                title=raw_title,
                url=url
            )
            clean_title = OpportunityNormalizer.clean_job_title(raw_title)

            # Final validation gate
            is_valid, reason = OpportunityNormalizer.validate_job_listing(
                title=clean_title,
                company_name=company_name,
                primary_url=url,
                description=snippet_hint
            )
            if not is_valid:
                return False, None, reason

            work_arr, is_rem = OpportunityNormalizer.detect_work_arrangement(clean_title, snippet_hint, "")
            skills = OpportunityNormalizer.extract_skills_from_text(snippet_hint)
            salary = OpportunityNormalizer.extract_salary(snippet_hint)

            job = NormalizedJob(
                title=clean_title,
                company_name=company_name,
                description=snippet_hint,
                location=cls._extract_location_from_text(snippet_hint, url),
                is_remote=is_rem,
                work_arrangement=work_arr,
                employment_type="internship" if "intern" in clean_title.lower() else "full-time",
                primary_url=url,
                application_url=url,
                salary_range=salary,
                source_name=cls._identify_source(url),
                source_provider=source_provider,
                source_category=source_category,
                extracted_skills=skills,
                evidence_excerpt=snippet_hint[:300],
                confidence=confidence_hint if confidence_hint is not None else 0.85,
                extraction_quality=0.75,
                company_confidence=0.80 if company_name != "Direct Hiring Organization" else 0.50,
                verification_status=JobVerificationStatus.LISTING_FOUND_STATUS_UNVERIFIED.value,
                is_verified=False,
                verification_details={
                    "status": JobVerificationStatus.LISTING_FOUND_STATUS_UNVERIFIED.value,
                    "details": "Listing indexed by provider; direct page verification deferred."
                }
            )
            return True, job, None

        return False, None, "Insufficient accessible page content or search snippet."

    @classmethod
    def _extract_from_json_ld(
        cls,
        html: str,
        url: str,
        provider: str,
        category: str
    ) -> Optional[NormalizedJob]:
        """
        Extracts structured schema.org/JobPosting metadata from HTML ld+json blocks.
        """
        try:
            soup = BeautifulSoup(html, "html.parser")
            scripts = soup.find_all("script", type="application/ld+json")
            for s in scripts:
                if not s.string:
                    continue
                try:
                    data = json.loads(s.string)
                except Exception:
                    continue

                items = data if isinstance(data, list) else (data.get("@graph", []) if isinstance(data, dict) and "@graph" in data else [data])
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    item_type = item.get("@type")
                    if item_type == "JobPosting" or (isinstance(item_type, list) and "JobPosting" in item_type):
                        raw_title = item.get("title") or item.get("name")
                        if not raw_title or len(raw_title.strip()) < 3:
                            continue

                        # Clean Title
                        clean_title = OpportunityNormalizer.clean_job_title(raw_title)

                        # Employer
                        hiring_org = item.get("hiringOrganization")
                        org_name = None
                        if isinstance(hiring_org, dict):
                            org_name = hiring_org.get("name")
                        elif isinstance(hiring_org, str):
                            org_name = hiring_org

                        resolved_employer = OpportunityNormalizer.clean_employer_name(
                            company_name=org_name or "Direct Employer",
                            title=clean_title,
                            url=url
                        )

                        # Location
                        loc_str = "India"
                        job_loc = item.get("jobLocation")
                        if isinstance(job_loc, dict):
                            addr = job_loc.get("address", {})
                            if isinstance(addr, dict):
                                parts = [addr.get("addressLocality"), addr.get("addressRegion"), addr.get("addressCountry")]
                                loc_str = ", ".join([p for p in parts if p and isinstance(p, str)]) or "India"
                            elif isinstance(addr, str):
                                loc_str = addr

                        # Remote
                        is_remote = item.get("jobLocationType") == "TELECOMMUTE" or "remote" in (clean_title + " " + str(loc_str)).lower()
                        work_arr = "remote" if is_remote else "onsite"

                        # Description
                        raw_desc = item.get("description", "")
                        clean_desc = BeautifulSoup(raw_desc, "html.parser").get_text(separator=" ").strip() if raw_desc else ""

                        # Salary
                        salary_str = None
                        salary_data = item.get("baseSalary")
                        if isinstance(salary_data, dict):
                            val = salary_data.get("value")
                            currency = salary_data.get("currency", "")
                            if isinstance(val, dict):
                                min_val = val.get("minValue")
                                max_val = val.get("maxValue")
                                if min_val and max_val:
                                    salary_str = f"{currency} {min_val} - {max_val}"
                            elif isinstance(val, (int, float, str)):
                                salary_str = f"{currency} {val}"

                        # Application URL
                        app_url = item.get("directApply") or item.get("url") or url

                        # Skills
                        skills = OpportunityNormalizer.extract_skills_from_text(clean_desc)

                        return NormalizedJob(
                            title=clean_title,
                            company_name=resolved_employer,
                            description=clean_desc[:2000] if clean_desc else clean_title,
                            location=loc_str,
                            is_remote=is_remote,
                            work_arrangement=work_arr,
                            employment_type=str(item.get("employmentType") or "full-time").lower(),
                            primary_url=url,
                            application_url=str(app_url),
                            salary_range=salary_str,
                            source_name=cls._identify_source(url),
                            source_provider=provider,
                            source_category=category,
                            posting_date=str(item.get("datePosted")) if item.get("datePosted") else None,
                            extracted_skills=skills,
                            evidence_excerpt=clean_desc[:300] if clean_desc else None,
                            confidence=0.95,
                            extraction_quality=0.95,
                            company_confidence=0.90 if resolved_employer != "Direct Hiring Organization" else 0.60
                        )
        except Exception as e:
            logger.debug(f"JSON-LD extraction error for {url}: {e}")
        return None

    @classmethod
    def _extract_from_html_tags(
        cls,
        html: str,
        url: str,
        provider: str,
        category: str,
        snippet_fallback: Optional[str] = None
    ) -> Optional[NormalizedJob]:
        """
        Extracts title, employer, and location from OpenGraph meta tags and standard HTML headings.
        """
        try:
            soup = BeautifulSoup(html, "html.parser")
            
            # Title
            og_title = soup.find("meta", property="og:title")
            title_text = og_title.get("content") if og_title else (soup.title.string if soup.title else None)
            if not title_text:
                h1 = soup.find("h1")
                title_text = h1.get_text().strip() if h1 else None

            if not title_text:
                return None

            clean_title = OpportunityNormalizer.clean_job_title(title_text)

            # Description
            og_desc = soup.find("meta", property="og:description")
            desc_text = og_desc.get("content") if og_desc else None
            if not desc_text:
                meta_desc = soup.find("meta", attrs={"name": "description"})
                desc_text = meta_desc.get("content") if meta_desc else snippet_fallback

            # Employer from tags or URL
            employer = OpportunityNormalizer.clean_employer_name(
                company_name=title_text.split(" - ")[-1] if " - " in title_text else "Direct Employer",
                title=clean_title,
                url=url
            )

            location = cls._extract_location_from_text(desc_text or "", url)
            work_arr, is_rem = OpportunityNormalizer.detect_work_arrangement(clean_title, desc_text or "", location)
            skills = OpportunityNormalizer.extract_skills_from_text(desc_text or "")
            salary = OpportunityNormalizer.extract_salary(desc_text or "")

            return NormalizedJob(
                title=clean_title,
                company_name=employer,
                description=(desc_text or clean_title)[:2000],
                location=location,
                is_remote=is_rem,
                work_arrangement=work_arr,
                employment_type="internship" if "intern" in clean_title.lower() else "full-time",
                primary_url=url,
                application_url=url,
                salary_range=salary,
                source_name=cls._identify_source(url),
                source_provider=provider,
                source_category=category,
                extracted_skills=skills,
                evidence_excerpt=(desc_text or "")[:300],
                confidence=0.85,
                extraction_quality=0.85,
                company_confidence=0.85 if employer != "Direct Hiring Organization" else 0.50
            )
        except Exception as e:
            logger.debug(f"HTML tag extraction error for {url}: {e}")
        return None

    @staticmethod
    def _extract_location_from_text(text: str, url: str) -> str:
        """
        Extracts verified location from listing text and URL instead of defaulting to search query.
        Ensures compound city names (e.g. Greater Noida, New Delhi) are evaluated before shorter variants (Noida, Delhi).
        """
        combined = f"{text} {url}".lower()
        
        # Check compound or multi-word cities first to prevent partial matches
        city_mapping = [
            ("greater noida", "Greater Noida"),
            ("new delhi", "New Delhi"),
            ("bengaluru", "Bengaluru"),
            ("bangalore", "Bengaluru"),
            ("gurugram", "Gurugram"),
            ("gurgaon", "Gurugram"),
            ("hyderabad", "Hyderabad"),
            ("noida", "Noida"),
            ("delhi", "Delhi"),
            ("mumbai", "Mumbai"),
            ("pune", "Pune"),
            ("chennai", "Chennai"),
            ("kolkata", "Kolkata"),
            ("mohali", "Mohali"),
            ("chandigarh", "Chandigarh"),
            ("jaipur", "Jaipur"),
            ("ahmedabad", "Ahmedabad"),
            ("kochi", "Kochi"),
            ("lucknow", "Lucknow"),
            ("indore", "Indore"),
            ("coimbatore", "Coimbatore"),
            ("visakhapatnam", "Visakhapatnam"),
        ]

        for term, canonical_name in city_mapping:
            if re.search(r"\b" + re.escape(term) + r"\b", combined):
                return canonical_name

        if "remote" in combined or "work from home" in combined or "wfh" in combined:
            return "Remote"
        return "India"

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
        elif any(ats in lower for ats in ["greenhouse.io", "lever.co", "ashbyhq.com", "workday.com"]):
            return "Company Career ATS"
        return "Company Career Page"
