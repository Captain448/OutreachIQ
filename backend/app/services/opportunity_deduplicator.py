import re
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
from typing import List, Dict, Tuple, Set, Optional
from app.services.providers.base_provider import NormalizedJob, NormalizedCompany
from app.services.opportunity_normalizer import OpportunityNormalizer

TRACKING_PARAMS = {
    'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
    'ref', 'trk', 'fbclid', 'gclid', 'subid', 'vjk'
}


class OpportunityDeduplicator:
    @staticmethod
    def canonicalize_url(url: str) -> str:
        """
        Normalizes and strips tracking parameters (utm_*, ref, trk, fbclid, etc.)
        from job posting URLs for deterministic duplicate detection.
        """
        if not url:
            return ""
        parts = urlsplit(url.strip())
        netloc = parts.netloc.lower()
        filtered_query = []
        if parts.query:
            for k, v in parse_qsl(parts.query, keep_blank_values=False):
                if k.lower() not in TRACKING_PARAMS and not k.lower().startswith("utm_"):
                    filtered_query.append((k, v))
            filtered_query.sort()
        new_query = urlencode(filtered_query)
        path = parts.path
        if len(path) > 1 and path.endswith("/"):
            path = path.rstrip("/")
        return urlunsplit((parts.scheme.lower(), netloc, path, new_query, ""))

    _canonicalize_url = canonicalize_url

    @staticmethod
    def deduplicate_jobs(jobs: List[NormalizedJob]) -> List[NormalizedJob]:
        """
        Deduplicates job postings across disparate providers (e.g. LinkedIn + Tavily + JSearch).
        Merges provenance links into primary_url and multi-source references.
        Filters out invalid or fragmented records using OpportunityNormalizer.
        """
        deduped: Dict[str, NormalizedJob] = {}
        url_to_key: Dict[str, str] = {}

        for job in jobs:
            # 1. Quality validation gate
            is_valid, _ = OpportunityNormalizer.validate_job_listing(
                title=job.title,
                company_name=job.company_name,
                primary_url=job.primary_url,
                description=job.description
            )
            if not is_valid:
                continue

            # 2. Canonicalize employer and title
            job.company_name = OpportunityNormalizer.clean_employer_name(
                company_name=job.company_name,
                title=job.title,
                url=job.primary_url
            )
            clean_url = OpportunityDeduplicator.canonicalize_url(job.primary_url)
            job.primary_url = clean_url  # Canonicalize in-place so persisted record is normalized
            norm_title = OpportunityNormalizer.normalize_title(job.title).lower()
            norm_company = job.company_name.strip().lower()
            norm_loc = (job.location or "").strip().lower()

            composite_key = f"{norm_company}::{norm_title}::{job.is_remote}"

            existing_key = None
            if clean_url in url_to_key:
                existing_key = url_to_key[clean_url]
            elif composite_key in deduped:
                existing_key = composite_key

            if existing_key and existing_key in deduped:
                existing = deduped[existing_key]
                # Combine extracted skills
                combined_skills = list(set(existing.extracted_skills + job.extracted_skills))
                existing.extracted_skills = sorted(combined_skills)
                # Keep richer description
                if len(job.description or "") > len(existing.description or ""):
                    existing.description = job.description
                # Combine source names
                if job.source_name not in existing.source_name:
                    existing.source_name = f"{existing.source_name}, {job.source_name}"
                # Keep the higher confidence
                existing.confidence = max(existing.confidence, job.confidence)
                # Ensure URL is tracked
                url_to_key[clean_url] = existing_key
            else:
                deduped[composite_key] = job
                url_to_key[clean_url] = composite_key

        return list(deduped.values())

    @staticmethod
    def deduplicate_companies(companies: List[NormalizedCompany]) -> List[NormalizedCompany]:
        """
        Deduplicates companies discovered via different queries or providers.
        """
        deduped: Dict[str, NormalizedCompany] = {}

        for comp in companies:
            norm_name = comp.name.strip().lower()
            domain = comp.domain.lower() if comp.domain else None
            key = domain if domain else norm_name

            if key in deduped:
                existing = deduped[key]
                # Merge signals
                existing.signals.extend(comp.signals)
                if len(comp.description or "") > len(existing.description or ""):
                    existing.description = comp.description
                existing.confidence = max(existing.confidence, comp.confidence)
            else:
                deduped[key] = comp

        return list(deduped.values())

    @staticmethod
    def _canonicalize_url(url: str) -> str:
        # Strip tracking query params (?utm_source=..., &ref=...)
        clean = re.sub(r"[?&](utm_[^&]+|ref=[^&]+|trk=[^&]+|fbclid=[^&]+)", "", url)
        # Remove trailing slash
        clean = clean.rstrip("/")
        return clean
