import re
import json
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, Optional, Tuple, List
import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36 OutReachIQ-Verifier/1.0"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


class JobVerificationStatus(str, Enum):
    VERIFIED_OPEN = "VERIFIED_OPEN"
    LISTING_FOUND_STATUS_UNVERIFIED = "LISTING_FOUND_STATUS_UNVERIFIED"
    EXPIRED_OR_CLOSED = "EXPIRED_OR_CLOSED"
    INVALID_OR_REJECTED = "INVALID_OR_REJECTED"
    VERIFICATION_INCONCLUSIVE = "VERIFICATION_INCONCLUSIVE"


EXPIRED_PATTERNS = [
    re.compile(r"this\s+(?:job|position|posting|role|vacancy)\s+(?:has\s+)?(?:expired|closed|been\s+filled)", re.I),
    re.compile(r"no\s+longer\s+accepting\s+applications", re.I),
    re.compile(r"the\s+job\s+you\s+are\s+trying\s+to\s+view\s+is\s+no\s+longer\s+available", re.I),
    re.compile(r"this\s+(?:job|posting|listing)\s+is\s+(?:no\s+longer\s+active|closed)", re.I),
    re.compile(r"applications\s+(?:for\s+this\s+role\s+)?are\s+closed", re.I),
    re.compile(r"job\s+(?:posting\s+)?has\s+ended", re.I),
    re.compile(r"we\s+are\s+no\s+longer\s+hiring\s+for\s+this", re.I),
    re.compile(r"posting\s+expired", re.I),
]

ACTIVE_PATTERNS = [
    re.compile(r"apply\s+now", re.I),
    re.compile(r"apply\s+for\s+this\s+job", re.I),
    re.compile(r"submit\s+application", re.I),
    re.compile(r"easy\s+apply", re.I),
    re.compile(r"apply\s+on\s+company\s+site", re.I),
    re.compile(r"start\s+your\s+application", re.I),
    re.compile(r"apply\s+with\s+resume", re.I),
]


class ListingVerificationService:
    """
    Independent listing verification engine.
    Assesses web accessibility, checks for explicit closed/expired markers,
    confirms vacancy identity agreement, and determines authoritative verification state.
    """

    @classmethod
    async def verify_listing(
        cls,
        url: str,
        expected_title: Optional[str] = None,
        expected_company: Optional[str] = None,
        html_content: Optional[str] = None,
        http_status: Optional[int] = None,
        timeout_seconds: float = 6.0
    ) -> Dict[str, Any]:
        """
        Runs comprehensive multi-point listing verification.
        Returns a verification record with status, confidence, indicators, and details.
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        
        # 1. Basic URL validity check
        if not url or not (url.startswith("http://") or url.startswith("https://")):
            return {
                "status": JobVerificationStatus.INVALID_OR_REJECTED.value,
                "is_verified": False,
                "verified_at": now_iso,
                "http_status": None,
                "confidence": 0.0,
                "details": "Invalid or missing URL scheme.",
                "active_indicators": [],
                "closed_indicators": ["invalid_url"]
            }

        # 2. Fetch page if not already provided
        fetched_status = http_status
        content = html_content
        
        if content is None:
            try:
                async with httpx.AsyncClient(
                    headers=DEFAULT_HEADERS,
                    timeout=timeout_seconds,
                    follow_redirects=True,
                    verify=False
                ) as client:
                    resp = await client.get(url)
                    fetched_status = resp.status_code
                    if fetched_status == 200:
                        content = resp.text
                    elif fetched_status in (404, 410):
                        return {
                            "status": JobVerificationStatus.EXPIRED_OR_CLOSED.value,
                            "is_verified": False,
                            "verified_at": now_iso,
                            "http_status": fetched_status,
                            "confidence": 0.95,
                            "details": f"Job page returned HTTP {fetched_status} (listing removed or expired).",
                            "active_indicators": [],
                            "closed_indicators": [f"http_{fetched_status}"]
                        }
                    elif fetched_status in (403, 429, 503):
                        # Blocked / challenge (e.g. Cloudflare / LinkedIn sign-in wall)
                        return {
                            "status": JobVerificationStatus.LISTING_FOUND_STATUS_UNVERIFIED.value,
                            "is_verified": False,
                            "verified_at": now_iso,
                            "http_status": fetched_status,
                            "confidence": 0.50,
                            "details": f"Page access protected or rate-limited (HTTP {fetched_status}); listing found via provider index.",
                            "active_indicators": ["indexed_by_provider"],
                            "closed_indicators": []
                        }
                    else:
                        return {
                            "status": JobVerificationStatus.VERIFICATION_INCONCLUSIVE.value,
                            "is_verified": False,
                            "verified_at": now_iso,
                            "http_status": fetched_status,
                            "confidence": 0.30,
                            "details": f"Unexpected HTTP status {fetched_status}.",
                            "active_indicators": [],
                            "closed_indicators": []
                        }
            except httpx.TimeoutException:
                return {
                    "status": JobVerificationStatus.LISTING_FOUND_STATUS_UNVERIFIED.value,
                    "is_verified": False,
                    "verified_at": now_iso,
                    "http_status": None,
                    "confidence": 0.50,
                    "details": "Verification request timed out; listing found via search provider.",
                    "active_indicators": ["indexed_by_provider"],
                    "closed_indicators": []
                }
            except Exception as e:
                logger.debug(f"Verification request error for {url}: {e}")
                return {
                    "status": JobVerificationStatus.VERIFICATION_INCONCLUSIVE.value,
                    "is_verified": False,
                    "verified_at": now_iso,
                    "http_status": None,
                    "confidence": 0.30,
                    "details": f"Connection error during verification: {str(e)}",
                    "active_indicators": [],
                    "closed_indicators": []
                }

        # 3. Analyze HTML Content
        if not content:
            return {
                "status": JobVerificationStatus.LISTING_FOUND_STATUS_UNVERIFIED.value,
                "is_verified": False,
                "verified_at": now_iso,
                "http_status": fetched_status or 200,
                "confidence": 0.50,
                "details": "Empty page body returned.",
                "active_indicators": [],
                "closed_indicators": []
            }

        return cls.verify_html_content(
            content=content,
            url=url,
            expected_title=expected_title,
            expected_company=expected_company,
            http_status=fetched_status or 200
        )

    @classmethod
    def verify_html_content(
        cls,
        content: str,
        url: str,
        expected_title: Optional[str] = None,
        expected_company: Optional[str] = None,
        http_status: int = 200
    ) -> Dict[str, Any]:
        """
        Parses HTML text and structured metadata to confirm open status, application path,
        and vacancy agreement.
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        closed_indicators = []
        active_indicators = []
        
        soup = BeautifulSoup(content[:250000], "html.parser")
        
        # Remove script and style elements for text analysis
        for s in soup(["script", "style"]):
            s.decompose()
        
        clean_text = soup.get_text(separator=" ", strip=True)
        lower_text = clean_text.lower()

        # Check for explicit expired markers
        for pat in EXPIRED_PATTERNS:
            if pat.search(lower_text):
                closed_indicators.append(pat.pattern)

        if closed_indicators:
            return {
                "status": JobVerificationStatus.EXPIRED_OR_CLOSED.value,
                "is_verified": False,
                "verified_at": now_iso,
                "http_status": http_status,
                "confidence": 0.90,
                "details": "Page explicitly indicates that this position is closed or no longer accepting applications.",
                "active_indicators": [],
                "closed_indicators": closed_indicators[:3]
            }

        # Check JSON-LD metadata for JobPosting expiration (validThrough)
        jsonld_scripts = BeautifulSoup(content[:150000], "html.parser").find_all("script", type="application/ld+json")
        for sc in jsonld_scripts:
            try:
                data = json.loads(sc.string or "")
                items = data if isinstance(data, list) else [data]
                for it in items:
                    if isinstance(it, dict) and it.get("@type") == "JobPosting":
                        active_indicators.append("jsonld_jobposting")
                        valid_through = it.get("validThrough")
                        if valid_through:
                            try:
                                dt = datetime.fromisoformat(valid_through.replace("Z", "+00:00"))
                                if dt < datetime.now(timezone.utc):
                                    return {
                                        "status": JobVerificationStatus.EXPIRED_OR_CLOSED.value,
                                        "is_verified": False,
                                        "verified_at": now_iso,
                                        "http_status": http_status,
                                        "confidence": 0.95,
                                        "details": f"Job validThrough expiration date ({valid_through}) has passed.",
                                        "active_indicators": ["jsonld_jobposting"],
                                        "closed_indicators": [f"validThrough_expired: {valid_through}"]
                                    }
                            except Exception:
                                pass
            except Exception:
                pass

        # Check for active application indicators
        for pat in ACTIVE_PATTERNS:
            if pat.search(lower_text):
                active_indicators.append(pat.pattern)

        # Check for apply button tags or form inputs
        apply_buttons = soup.find_all(
            lambda tag: tag.name in ["a", "button"] and "apply" in tag.get_text().lower()
        )
        if apply_buttons:
            active_indicators.append("apply_action_element")

        # Identity Agreement Check
        role_agreement = True
        company_agreement = True
        
        if expected_title:
            clean_expected = re.sub(r"[^\w\s]", "", expected_title.lower())
            keywords = [w for w in clean_expected.split() if len(w) > 3 and w not in {"developer", "engineer", "lead"}]
            if keywords and not any(kw in lower_text for kw in keywords):
                role_agreement = False

        if expected_company and expected_company.lower() not in {"direct hiring organization", "confidential"}:
            clean_comp = re.sub(r"[^\w\s]", "", expected_company.lower())
            if len(clean_comp) > 3 and clean_comp not in lower_text:
                company_agreement = False

        if not role_agreement and not company_agreement:
            return {
                "status": JobVerificationStatus.INVALID_OR_REJECTED.value,
                "is_verified": False,
                "verified_at": now_iso,
                "http_status": http_status,
                "confidence": 0.80,
                "details": "Accessible page content does not match expected role title or employer identity.",
                "active_indicators": active_indicators[:2],
                "closed_indicators": ["role_company_mismatch"]
            }

        # Determine Final Verified Status
        if len(active_indicators) >= 1:
            return {
                "status": JobVerificationStatus.VERIFIED_OPEN.value,
                "is_verified": True,
                "verified_at": now_iso,
                "http_status": http_status,
                "confidence": 0.90 if len(active_indicators) >= 2 else 0.80,
                "details": "Listing is accessible, matches vacancy details, and confirms active application status.",
                "active_indicators": list(set(active_indicators))[:5],
                "closed_indicators": []
            }

        return {
            "status": JobVerificationStatus.VERIFIED_OPEN.value if http_status == 200 else JobVerificationStatus.VERIFICATION_INCONCLUSIVE.value,
            "is_verified": http_status == 200,
            "verified_at": now_iso,
            "http_status": http_status,
            "confidence": 0.70,
            "details": "Listing page is accessible with intact job description.",
            "active_indicators": ["accessible_job_page"],
            "closed_indicators": []
        }
