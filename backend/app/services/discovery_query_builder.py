import re
from typing import List, Dict, Any, Optional, Set


# Role taxonomy mapping canonical target roles to closely related variations
ROLE_VARIATIONS: Dict[str, List[str]] = {
    "ai/ml engineer": [
        "Machine Learning Engineer", "AI Engineer", "Applied AI Engineer",
        "NLP Engineer", "Computer Vision Engineer", "Data Scientist", "Deep Learning Engineer"
    ],
    "machine learning engineer": [
        "AI/ML Engineer", "AI Engineer", "Applied Machine Learning Engineer",
        "MLOps Engineer", "Data Scientist"
    ],
    "full stack developer": [
        "Full Stack Engineer", "Full Stack Software Engineer", "Software Engineer",
        "Backend Developer", "Frontend Developer"
    ],
    "backend developer": [
        "Backend Engineer", "Software Engineer", "Python Developer",
        "Cloud Backend Engineer", "API Engineer"
    ],
    "frontend developer": [
        "Frontend Engineer", "UI Engineer", "Web Developer",
        "Angular Developer", "React Developer"
    ],
    "data engineer": [
        "Data Platform Engineer", "ETL Developer", "Big Data Engineer",
        "Analytics Engineer"
    ],
    "software engineer": [
        "Software Developer", "Backend Engineer", "Full Stack Developer",
        "Member of Technical Staff", "Systems Engineer"
    ],
    "devops engineer": [
        "Site Reliability Engineer", "SRE", "Cloud Engineer",
        "Infrastructure Engineer", "Platform Engineer"
    ]
}

# Supported accessible source domains for targeted discovery
ACCESSIBLE_SOURCES: Dict[str, Dict[str, Any]] = {
    "linkedin": {
        "name": "LinkedIn (Public Search)",
        "site_clause": "site:linkedin.com/jobs/view OR site:linkedin.com/jobs",
        "category": "Direct Employer / Network"
    },
    "naukri": {
        "name": "Naukri",
        "site_clause": "site:naukri.com/job-listings",
        "category": "Public Career Feed"
    },
    "internshala": {
        "name": "Internshala",
        "site_clause": "site:internshala.com/job/detail OR site:internshala.com/internship/detail",
        "category": "Internships & Freshers"
    },
    "unstop": {
        "name": "Unstop",
        "site_clause": "site:unstop.com/jobs OR site:unstop.com/internships",
        "category": "Campus & Early Career"
    },
    "wellfound": {
        "name": "Wellfound",
        "site_clause": "site:wellfound.com/jobs OR site:wellfound.com/company",
        "category": "Startup Careers"
    },
    "ats_portals": {
        "name": "Employer ATS Career Pages",
        "site_clause": "site:greenhouse.io OR site:lever.co OR site:ashbyhq.com OR site:workday.com OR inurl:careers",
        "category": "Direct Company Portals"
    }
}


class DiscoveryQueryBuilder:
    @staticmethod
    def get_role_variations(primary_role: str) -> List[str]:
        """
        Returns closely related role variations without broadening to unrelated domains.
        """
        if not primary_role:
            return ["Software Engineer"]

        clean = primary_role.strip().lower()
        # Direct lookup
        for key, variations in ROLE_VARIATIONS.items():
            if key in clean or clean in key:
                return [primary_role.strip()] + [v for v in variations if v.lower() != clean][:3]

        # Check keywords
        if "ai" in clean or "ml" in clean or "machine learning" in clean:
            return [primary_role.strip(), "Machine Learning Engineer", "Applied AI Engineer"]
        elif "backend" in clean:
            return [primary_role.strip(), "Backend Engineer", "Software Engineer"]
        elif "frontend" in clean:
            return [primary_role.strip(), "Frontend Engineer", "UI Developer"]
        elif "full" in clean and "stack" in clean:
            return [primary_role.strip(), "Full Stack Engineer", "Software Developer"]

        return [primary_role.strip()]

    @staticmethod
    def build_targeted_queries(
        target_roles: List[str],
        skills: List[str],
        locations: Optional[List[str]] = None,
        remote_preference: str = "flexible",
        experience_level: str = "mid",
        work_arrangement: Optional[str] = None,
        employment_type: Optional[str] = None,
        limit_queries: int = 6
    ) -> List[Dict[str, Any]]:
        """
        Constructs bounded, diversified queries across ATS portals, public LinkedIn,
        Naukri, Internshala, and Wellfound using candidate preferences and multi-location targets.
        """
        queries: List[Dict[str, Any]] = []

        primary_role = target_roles[0] if target_roles else "Software Engineer"
        role_vars = DiscoveryQueryBuilder.get_role_variations(primary_role)
        top_skills = [s for s in skills if len(s) > 1][:3]
        skills_str = " ".join(top_skills) if top_skills else ""

        # Multi-location clause formatting
        if locations:
            clean_locs = [l.strip() for l in locations if l and l.strip()]
            if len(clean_locs) == 1:
                loc = f'"{clean_locs[0]}"' if " " in clean_locs[0] else clean_locs[0]
            elif len(clean_locs) > 1:
                joined_locs = " OR ".join(f'"{l}"' if " " in l else l for l in clean_locs[:3])
                loc = f"({joined_locs})"
            else:
                loc = "India"
        else:
            loc = "India"

        is_remote = remote_preference == "remote" or (work_arrangement and work_arrangement.lower() == "remote")
        is_hybrid = work_arrangement and work_arrangement.lower() == "hybrid"
        remote_str = "Remote" if is_remote else ("Hybrid" if is_hybrid else "")

        exp_str = ""
        emp_lower = (employment_type or "").lower()
        if "intern" in emp_lower or experience_level in ("entry", "fresher", "intern"):
            exp_str = "internship OR fresher OR junior"
        elif "contract" in emp_lower:
            exp_str = "contract"

        # 1. Employer ATS Portals Query (Greenhouse, Lever, Ashby, Workday, etc.)
        ats_clause = ACCESSIBLE_SOURCES["ats_portals"]["site_clause"]
        q_ats = f'"{role_vars[0]}" {skills_str} {remote_str} {loc} ({ats_clause})'.strip()
        queries.append({
            "query": re.sub(r"\s+", " ", q_ats),
            "source_category": "Direct Company Portals",
            "source_key": "ats_portals",
            "intended_source": "Employer ATS Career Pages"
        })

        # 2. Public LinkedIn Jobs Query
        linkedin_clause = ACCESSIBLE_SOURCES["linkedin"]["site_clause"]
        q_li = f'"{role_vars[0]}" {skills_str} {loc} ({linkedin_clause})'.strip()
        queries.append({
            "query": re.sub(r"\s+", " ", q_li),
            "source_category": "Direct Employer / Network",
            "source_key": "linkedin",
            "intended_source": "LinkedIn (Public Search)"
        })

        # 3. Primary Regional Feed (Naukri individual listings)
        naukri_clause = ACCESSIBLE_SOURCES["naukri"]["site_clause"]
        q_nk = f'"{role_vars[0]}" {skills_str} {loc} ({naukri_clause})'.strip()
        queries.append({
            "query": re.sub(r"\s+", " ", q_nk),
            "source_category": "Public Career Feed",
            "source_key": "naukri",
            "intended_source": "Naukri"
        })

        # 4. Secondary Role Variation Query (e.g. Machine Learning Engineer or Backend Engineer)
        if len(role_vars) > 1:
            second_role = role_vars[1]
            q_var = f'"{second_role}" {skills_str} {loc} {remote_str} ({ats_clause} OR {naukri_clause})'.strip()
            queries.append({
                "query": re.sub(r"\s+", " ", q_var),
                "source_category": "Direct Company Portals",
                "source_key": "role_variant",
                "intended_source": "Multi-Source Role Variant"
            })

        # 5. Internships & Freshers / Early Career (if applicable)
        if exp_str:
            internshala_clause = ACCESSIBLE_SOURCES["internshala"]["site_clause"]
            q_early = f'"{role_vars[0]}" {loc} ({exp_str}) ({internshala_clause})'.strip()
            queries.append({
                "query": re.sub(r"\s+", " ", q_early),
                "source_category": "Internships & Freshers",
                "source_key": "internshala",
                "intended_source": "Internshala"
            })
        else:
            # Wellfound / Startup Query
            wellfound_clause = ACCESSIBLE_SOURCES["wellfound"]["site_clause"]
            q_wf = f'"{role_vars[0]}" {skills_str} {loc} {remote_str} ({wellfound_clause})'.strip()
            queries.append({
                "query": re.sub(r"\s+", " ", q_wf),
                "source_category": "Startup Careers",
                "source_key": "wellfound",
                "intended_source": "Wellfound"
            })

        return queries[:limit_queries]
