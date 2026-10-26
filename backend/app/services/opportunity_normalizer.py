import re
from typing import List, Tuple, Set, Optional, Dict, Any
from urllib.parse import urlparse
from app.services.resume_parser import KNOWN_SKILLS

# Known job aggregator / search engine domains and portal names
AGGREGATOR_NAMES = {
    "naukri", "internshala", "linkedin", "indeed", "glassdoor", "unstop",
    "foundit", "monster", "shine", "timesjobs", "freshersworld", "google",
    "hirist", "instahyre", "wellfound", "angel.co", "simplyhired"
}

# Recognized standard enterprise corporations for honest classification
KNOWN_ENTERPRISES = {
    "google", "microsoft", "amazon", "apple", "meta", "netflix", "ibm",
    "oracle", "cisco", "cisco systems", "intel", "adobe", "salesforce", "infosys",
    "tcs", "tata consultancy services", "wipro", "hcl", "hcltech", "cognizant",
    "accenture", "capgemini", "deloitte", "pwc", "ey", "kpmg", "samsung",
    "nvidia", "qualcomm", "jpmorgan", "jpmorgan chase", "goldman sachs",
    "morgan stanley", "uber", "airbnb", "siemens", "sap", "sony", "bosch",
    "walmart", "target", "flipkart", "swiggy", "zomato", "reliance", "tata",
    "l&t", "larsen & toubro", "tech mahindra", "genpact", "atlassian",
    "intuit", "stripe", "shopify", "servicenow", "paypal"
}

# Known cities and regions to prevent locations from being mistaken for company names
KNOWN_LOCATIONS = {
    "gurugram", "gurgaon", "noida", "delhi", "new delhi", "bengaluru", "bangalore",
    "mumbai", "pune", "hyderabad", "chennai", "kolkata", "ahmedabad", "mohali",
    "chandigarh", "jaipur", "kochi", "coimbatore", "indore", "india", "remote",
    "london", "new york", "san francisco", "seattle", "austin", "toronto", "singapore",
    "greater noida", "navi mumbai", "panchkula"
}

# Common role keywords that characterize legitimate job positions
VALID_ROLE_KEYWORDS = {
    "engineer", "developer", "architect", "scientist", "analyst", "specialist",
    "lead", "manager", "intern", "internship", "consultant", "designer",
    "administrator", "programmer", "researcher", "fellow", "associate",
    "technician", "officer", "director", "head", "practitioner"
}


class OpportunityNormalizer:
    @staticmethod
    def normalize_title(title: str) -> str:
        """
        Normalizes variations of job titles to a clean, canonical representation.
        e.g., 'Sr. Software Dev (Remote)' -> 'Senior Software Developer'
        """
        if not title:
            return ""

        cleaned = title.strip()
        # Clean multi-line or emoji noise (e.g. LinkedIn / social posts: '🚀 We Are Hiring – ...')
        lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
        if lines:
            cleaned = lines[0]
        # Remove emojis and special symbols
        cleaned = re.sub(r"[^\w\s\(\)\[\]\-–|/.,;:&]", " ", cleaned)
        cleaned = cleaned.strip().lower()

        # Remove "we are hiring", "hiring for", "urgent requirement for", etc.
        cleaned = re.sub(r"^(we\s+are\s+hiring|hiring\s+for|urgent\s+opening\s+for|urgent\s+requirement\s+for|wanted\s+immediately|looking\s+for)\s*[-–:]*\s*", "", cleaned)

        # Remove parenthetical notes
        cleaned = re.sub(r"\(.*?\)", "", cleaned)
        cleaned = re.sub(r"\[.*?\]", "", cleaned)
        # Remove suffix after dash or pipe if it contains company/location
        cleaned = re.sub(r"[-–|/].*", "", cleaned)

        # Standard replacements (handles sr., jr., dev, swe, etc.)
        cleaned = re.sub(r"\bsr\b\.?", "senior", cleaned)
        cleaned = re.sub(r"\bjr\b\.?", "junior", cleaned)
        cleaned = re.sub(r"\bdev\b\.?", "developer", cleaned)
        cleaned = re.sub(r"\bswe\b\.?", "software engineer", cleaned)
        cleaned = re.sub(r"\bfullstack\b", "full stack", cleaned)
        cleaned = re.sub(r"\bml\b\.?", "machine learning", cleaned)
        cleaned = re.sub(r"\bai\b\.?", "artificial intelligence", cleaned)

        # Remove stray punctuation
        cleaned = re.sub(r"[.,;:_]", " ", cleaned)

        words = [w.capitalize() for w in cleaned.split() if len(w) > 1]
        return " ".join(words) if words else title.strip()

    @staticmethod
    def clean_job_title(title: str) -> str:
        """
        Extracts a clean, single-line job title free from social media emojis and headers.
        """
        if not title:
            return ""

        # Check for multi-line hiring posts
        lines = [line.strip() for line in title.splitlines() if line.strip()]
        first_line = lines[0] if lines else title

        # Strip emojis and leading bullet points
        cleaned = re.sub(r"^[^\w\s]+", "", first_line).strip()

        # Strip prefixes like 'We Are Hiring –', 'Job Overview:', 'Role:'
        cleaned = re.sub(r"^(we\s+are\s+hiring|hiring\s+–|hiring\s+-|role\s*:|job\s+overview\s*:)\s*", "", cleaned, flags=re.IGNORECASE).strip()

        # Split on company suffixes like ' at ...', ' - ...', ' | ...'
        for sep in [" at ", " - ", " – ", " | ", ": "]:
            if sep in cleaned:
                parts = cleaned.split(sep)
                # Keep the part that contains a role keyword if possible
                for p in parts:
                    if any(rk in p.lower() for rk in VALID_ROLE_KEYWORDS):
                        cleaned = p.strip()
                        break
                else:
                    cleaned = parts[0].strip()

        # Clean trailing location hints like ' in Mohali, Punjab'
        cleaned = re.sub(r"\s+in\s+[\w\s,]+$", "", cleaned, flags=re.IGNORECASE)

        return cleaned.strip() or title.strip()

    @staticmethod
    def validate_job_listing(
        title: str,
        company_name: str,
        primary_url: str,
        description: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Rigorous Quality Gate:
        Evaluates whether a discovered record is genuinely an advertised job opportunity.
        Rejects pagination, directory aggregations, search-page fragments, and invalid URLs.
        """
        if not title or len(title.strip()) < 3:
            return False, "Title is missing or excessively short."

        raw_title = title.strip()
        lower_title = raw_title.lower()

        # 1. URL Validation
        if not primary_url or not isinstance(primary_url, str):
            return False, "Missing listing URL."
        try:
            parsed = urlparse(primary_url)
            if parsed.scheme not in ("http", "https") or not parsed.netloc:
                return False, f"Invalid URL scheme or missing host: {primary_url}"
        except Exception:
            return False, f"Malformed URL: {primary_url}"

        # 2. Reject Pagination Headings (e.g. 'Page 5259', 'Page 2 of 10')
        if re.search(r"^\s*page\s+\d+\b", lower_title):
            return False, f"Title represents pagination index: '{raw_title}'"
        if re.search(r"^\s*\d+\s*$", lower_title):
            return False, f"Title is numeric only: '{raw_title}'"

        # 3. Reject Job Directory Aggregations & Search Count Headings
        # e.g., '203 C Engineer Job Vacancies In Mohali', '100 React Js Developer Job Vacancies',
        # '40 Machine Learning Work From Home Fresher Jobs in ...'
        if re.search(r"^\s*\d+\+?\s+.*\s+(jobs?|vacanc(y|ies)|openings?)\b", lower_title):
            return False, f"Title represents an aggregated search directory count: '{raw_title}'"

        if re.search(r"\b(job\s+vacancies\s+in|jobs\s+in\s+[a-z]+|fresher\s+jobs\s+in|work\s+from\s+home\s+fresher\s+jobs)\b", lower_title):
            return False, f"Title represents a regional search results directory: '{raw_title}'"

        # 4. Reject Company Directory / Search Fragment Headings
        # e.g., 'Pione Technologies Llp Jobs', 'Xyz Corp Careers', 'Search Jobs'
        if re.search(r"^[a-z0-9\s.,&'-]+\s+(llp|pvt\s+ltd|ltd|inc|corp|technologies|solutions)?\s+jobs\s*$", lower_title):
            # Check if there is an actual role inside
            if not any(rk in lower_title for rk in VALID_ROLE_KEYWORDS):
                return False, f"Title represents a company job directory heading: '{raw_title}'"

        # 5. Reject Generic Website / Navigation Fragments
        generic_fragments = [
            "about us", "contact us", "privacy policy", "terms of service", "careers at",
            "search jobs", "all open positions", "job search results", "browse jobs",
            "view all jobs", "login", "sign up", "register", "home page"
        ]
        for gf in generic_fragments:
            if lower_title == gf or lower_title.startswith(gf + " -") or lower_title.startswith(gf + " |"):
                return False, f"Title is a generic site navigation fragment: '{raw_title}'"

        # 6. Validate Role Substance
        # Must contain at least one plausible role keyword OR software/engineering terminology
        has_role_keyword = any(rk in lower_title for rk in VALID_ROLE_KEYWORDS)
        has_skill_keyword = any(sk in lower_title for sk in ["python", "java", "react", "angular", "ai", "ml", "frontend", "backend", "full stack", "cloud", "devops", "net", "c++"])
        
        if not (has_role_keyword or has_skill_keyword):
            return False, f"Title does not contain recognized role or technical occupation keywords: '{raw_title}'"

        # 7. Validate Company Substance
        if not company_name or len(company_name.strip()) < 2:
            return False, "Company name is missing or too short."
        
        lower_comp = company_name.strip().lower()
        if lower_comp in {"unknown organization", "page", "null", "undefined", "in"}:
            return False, f"Company name is invalid or uninformative: '{company_name}'"

        return True, None

    @staticmethod
    def clean_employer_name(company_name: str, title: str, url: str) -> str:
        """
        Ensures job board aggregators (Naukri, Internshala, LinkedIn), pagination markers,
        and geographic locations are not erroneously labeled as the hiring employer.
        Extracts true employer when available.
        """
        raw = company_name.strip() if company_name else ""
        # Strip aggregator prefixes (e.g. "Naukri.com - Infosys Limited", "Indeed: Google")
        raw = re.sub(
            r"^(?:https?://)?(?:www\.)?(?:naukri(?:\.com)?|indeed(?:\.com)?|internshala(?:\.com)?|linkedin(?:\.com)?|glassdoor(?:\.com)?)\s*[-–|:]\s*",
            "",
            raw,
            flags=re.IGNORECASE
        ).strip()
        lower = raw.lower()

        # Check if company_name is an aggregator, a known city/region, a pagination index, or directory count
        is_aggregator = lower in AGGREGATOR_NAMES or any(lower == agg or lower.startswith(agg + " ") or lower.endswith(" " + agg) for agg in AGGREGATOR_NAMES)
        is_location = lower in KNOWN_LOCATIONS
        is_pagination = bool(re.search(r"^\s*page\s+\d+(\s+of\s+\d+)?\s*$", lower)) or bool(re.search(r"^\s*\d+\s*$", lower))
        is_dir_count = bool(re.search(r"^\s*\d+\+?\s+.*\s+(jobs?|vacanc(y|ies)|openings?|internships?)\b", lower))
        # Role terms mistaken as company names
        is_role_name = any(lower == rk or lower.startswith(rk + " ") for rk in ["ai", "ai engineer", "software engineer", "developer", "engineer", "full stack", "backend", "frontend"])
        is_generic = lower in {"unknown organization", "page", "null", "undefined", "in", "direct employer", "hiring", "jobs", "careers"}

        if is_aggregator or is_location or is_pagination or is_dir_count or is_generic or is_role_name:
            # 1. Try extracting from Employer ATS URLs (Greenhouse, Lever, Ashby, Workday)
            if "greenhouse.io" in url:
                m_gh = re.search(r"(?:boards|job-boards)\.greenhouse\.io/([^/?#]+)", url)
                if m_gh:
                    slug = m_gh.group(1).replace("-", " ").strip()
                    if len(slug) >= 2:
                        return slug.title()

            if "lever.co" in url:
                m_lv = re.search(r"jobs\.lever\.co/([^/?#]+)", url)
                if m_lv:
                    slug = m_lv.group(1).replace("-", " ").strip()
                    if len(slug) >= 2:
                        return slug.title()

            if "ashbyhq.com" in url:
                m_ashby = re.search(r"jobs\.ashbyhq\.com/([^/?#]+)", url)
                if m_ashby:
                    slug = m_ashby.group(1).replace("-", " ").strip()
                    if len(slug) >= 2:
                        return slug.title()

            if "myworkdayjobs.com" in url:
                m_wd = re.search(r"https?://([^.]+)\.(?:wd\d+\.)?myworkdayjobs\.com", url)
                if m_wd:
                    slug = m_wd.group(1).replace("-", " ").strip()
                    if len(slug) >= 2:
                        return slug.title()

            # 2. Try extracting from Naukri job listing URL:
            # e.g., https://www.naukri.com/job-listings-ai-ml-engineer-with-knowledge-of-front-end-visioapps-technology-gurugram-0-to-4-years-131026036420
            # e.g., https://www.naukri.com/job-listings-mern-stack-developer-relinns-technologies-mohali-1-to-4-years-060225502955
            if "naukri.com" in url:
                m_listing = re.search(r"/job-listings-(.+?)-(?:[0-9]+-to-[0-9]+-years|\d+-years)-[0-9]+", url)
                if m_listing:
                    slug_body = m_listing.group(1)
                    parts = slug_body.split("-")
                    # Check if last part or second to last part is a known location
                    if len(parts) >= 2 and parts[-1] in KNOWN_LOCATIONS:
                        comp_words = [p.capitalize() for p in parts[-3:-1] if p not in KNOWN_LOCATIONS]
                        comp_candidate = " ".join(comp_words)
                        if comp_candidate and len(comp_candidate) > 2:
                            return comp_candidate
                    elif len(parts) >= 3 and parts[-2] in KNOWN_LOCATIONS:
                        comp_words = [p.capitalize() for p in parts[-4:-2] if p not in KNOWN_LOCATIONS]
                        comp_candidate = " ".join(comp_words)
                        if comp_candidate and len(comp_candidate) > 2:
                            return comp_candidate

                # Check for /<company-name>-jobs-<id> (e.g. /iweb-technologies-jobs-5259)
                m_comp_jobs = re.search(r"/([a-z0-9\-]+)-jobs-\d+", url)
                if m_comp_jobs:
                    slug = m_comp_jobs.group(1)
                    words = [w.capitalize() for w in slug.split("-") if w.lower() not in AGGREGATOR_NAMES and w.lower() not in KNOWN_LOCATIONS]
                    if words:
                        return " ".join(words)

            # 2. Try extracting from Internshala URL:
            if "internshala.com" in url:
                m_is = re.search(r"-at-([a-z0-9\-]+?)(?:\d+)?(?:/|$)", url)
                if m_is:
                    slug = m_is.group(1)
                    words = [w.capitalize() for w in slug.split("-") if w.lower() not in AGGREGATOR_NAMES and w.lower() not in KNOWN_LOCATIONS]
                    if words:
                        return " ".join(words)

            # 3. Check if title has 'at <Company>'
            match = re.search(r"\bat\s+([A-Z][A-Za-z0-9\s&.,'-]+)", title)
            if match:
                candidate = match.group(1).strip()
                cand_lower = candidate.lower()
                if cand_lower not in AGGREGATOR_NAMES and cand_lower not in KNOWN_LOCATIONS and len(candidate) > 2:
                    return " ".join(candidate.split()[:4])
            
            # 4. Check for '<Company> hiring [for] <Role>'
            match_hiring = re.search(r"^([A-Z][A-Za-z0-9\s&.,'-]+?)\s+hiring(?:\s+for)?\b", title, re.IGNORECASE)
            if match_hiring:
                candidate = match_hiring.group(1).strip()
                cand_lower = candidate.lower()
                if cand_lower not in AGGREGATOR_NAMES and cand_lower not in KNOWN_LOCATIONS and len(candidate) > 2:
                    return " ".join(candidate.split()[:4])

            # 5. Try extracting domain name if not aggregator domain
            try:
                parsed = urlparse(url)
                domain = parsed.netloc.replace("www.", "")
                base = domain.split(".")[0].capitalize()
                if base.lower() not in AGGREGATOR_NAMES and base.lower() not in KNOWN_LOCATIONS and len(base) > 2:
                    return base
            except Exception:
                pass

            return "Direct Hiring Organization"

        # Clean trailing 'LLP Jobs', 'Pvt Ltd Jobs' etc.
        cleaned = re.sub(r"\s+jobs$", "", raw, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s+(llp|pvt\s+ltd)\s+jobs$", "", cleaned, flags=re.IGNORECASE)
        return cleaned.strip() or raw

    @staticmethod
    def classify_company(
        company_name: str,
        description: Optional[str] = None,
        domain: Optional[str] = None,
        signals_data: Optional[List[Dict[str, Any]]] = None,
        size_range: Optional[str] = None
    ) -> str:
        """
        Determines consistent company classification without fabrication:
        'startup' | 'smb' | 'mid_sized' | 'enterprise' | 'unknown'
        """
        if not company_name or company_name.strip().lower() in {"unknown", "direct hiring organization"}:
            return "unknown"

        lower_name = company_name.strip().lower()
        text = f"{company_name} {description or ''} {size_range or ''}".lower()

        # 1. Check verified global / Indian enterprises
        if any(ent in lower_name for ent in KNOWN_ENTERPRISES):
            return "enterprise"

        # 2. Check explicit headcount range if provided
        if size_range:
            sr_lower = size_range.lower()
            if any(term in sr_lower for term in ["10,000+", "5,000+", "100,000+"]):
                return "enterprise"
            if any(term in sr_lower for term in ["500-", "1,000-", "200-500", "500+", "1,000+"]):
                return "mid_sized"
            if any(term in sr_lower for term in ["51-200", "11-50"]):
                return "smb"
            if any(term in sr_lower for term in ["1-10", "1-50"]):
                if any(st in text for st in ["startup", "seed", "venture", "funded"]):
                    return "startup"
                return "smb"

        # 3. Check for enterprise corporate cues
        if any(term in text for term in [
            "multinational", "fortune 500", "enterprise leader", "publicly traded",
            "nasdaq:", "nyse:", "bse:", "nse:", "10,000+ employees", "5,000+ employees"
        ]):
            return "enterprise"

        # 4. Check for startup cues
        if any(term in text for term in [
            "startup", "early-stage", "seed funded", "series a", "series b",
            "series c", "y combinator", "venture-backed", "stealth", "pre-seed"
        ]):
            return "startup"

        # 5. Check for mid-sized cues
        if any(term in text for term in [
            "mid-market", "mid-sized", "500+ employees", "200-500 employees",
            "rapidly growing team", "regional offices"
        ]):
            return "mid_sized"

        # 6. Check for SMB cues
        if any(term in text for term in [
            "small business", "boutique agency", "consulting firm", "local agency",
            "family-owned", "specialized boutique", "it services and consulting"
        ]):
            return "smb"

        return "unknown"

    @staticmethod
    def extract_skills_from_text(text: str) -> List[str]:
        """
        Extracts verified skill keywords from job description or requirements text.
        """
        if not text:
            return []

        found: Set[str] = set()
        lower_text = text.lower()

        for skill in KNOWN_SKILLS:
            pattern = r"\b" + re.escape(skill) + r"\b"
            if re.search(pattern, lower_text):
                if skill in ["fastapi", "next.js", "node.js"]:
                    found.add(skill)
                elif skill == "ci/cd":
                    found.add("CI/CD")
                else:
                    found.add(skill.title() if len(skill) > 3 else skill.upper())

        return sorted(list(found))

    @staticmethod
    def detect_work_arrangement(title: str, description: str, location: str) -> Tuple[str, bool]:
        """
        Detects whether the job is remote, hybrid, or onsite.
        Returns: (work_arrangement, is_remote)
        """
        combined = f"{title} {description} {location}".lower()

        if "remote" in combined or "work from home" in combined or "wfh" in combined:
            return "remote", True
        elif "hybrid" in combined or "flexible" in combined:
            return "hybrid", False
        elif any(loc_hint in combined for loc_hint in ["onsite", "on-site", "office"]):
            return "onsite", False

        return "flexible", False

    @staticmethod
    def extract_salary(text: Optional[str]) -> Optional[str]:
        """
        Extracts verified salary references without fabricating figures.
        Returns formatted string if documented in text, else None.
        """
        if not text:
            return None

        # Look for ₹ / INR / LPA patterns (e.g. 6-10 LPA, ₹8,00,000)
        lpa_match = re.search(r"(\b\d+(\.\d+)?\s*[-–to]\s*\d+(\.\d+)?\s*(lpa|lac|lakh|lakhs)\b)", text, re.IGNORECASE)
        if lpa_match:
            return lpa_match.group(1).strip()

        inr_match = re.search(r"(₹\s*\d+[\d,]*(\s*[-–to]\s*₹?\s*\d+[\d,]*)?)", text)
        if inr_match:
            return inr_match.group(1).strip()

        usd_match = re.search(r"(\$\s*\d+[\d,]*\s*[-–to]\s*\$?\s*\d+[\d,]*(\s*(k|year|yr|hr|hour))?)", text, re.IGNORECASE)
        if usd_match:
            return usd_match.group(1).strip()

        return None
