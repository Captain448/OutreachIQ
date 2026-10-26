import re
from typing import Dict, Any, List, Set, Tuple
from app.core.config import settings
from app.models.opportunity import RecommendedAction, OpportunityType
from app.schemas.intelligence import CandidateIntelligenceRepresentation
from app.services.providers.base_provider import NormalizedJob, NormalizedCompany

# Domain clusters for semantic role matching
ROLE_CLUSTERS = {
    "ai_ml": {
        "keywords": [
            "ai", "ml", "artificial intelligence", "machine learning", "deep learning",
            "computer vision", "nlp", "natural language processing", "llm", "large language model",
            "genai", "generative ai", "prompt engineer", "ai engineer", "ml engineer",
            "data scientist", "machine learning scientist", "ai researcher"
        ],
        "core_skills": ["python", "pytorch", "tensorflow", "machine learning", "nlp", "llm", "docker"]
    },
    "frontend": {
        "keywords": [
            "frontend", "front end", "front-end", "ui", "ux", "react", "angular", "vue",
            "web developer", "javascript developer", "typescript developer", "css"
        ],
        "core_skills": ["javascript", "typescript", "react", "angular", "vue", "html", "css"]
    },
    "backend": {
        "keywords": [
            "backend", "back end", "back-end", "server", "api", "database", "python developer",
            "java developer", "golang developer", "node developer", "c# developer"
        ],
        "core_skills": ["python", "fastapi", "django", "node.js", "postgresql", "docker", "redis"]
    },
    "fullstack": {
        "keywords": ["full stack", "fullstack", "full-stack", "software engineer", "software developer"],
        "core_skills": ["javascript", "typescript", "python", "react", "postgresql"]
    },
    "devops": {
        "keywords": ["devops", "sre", "site reliability", "cloud", "infrastructure", "platform engineer", "kubernetes"],
        "core_skills": ["docker", "kubernetes", "aws", "gcp", "azure", "ci/cd", "linux"]
    },
    "data": {
        "keywords": ["data engineer", "data analytics", "bi engineer", "etl", "big data"],
        "core_skills": ["sql", "python", "spark", "hadoop", "postgresql"]
    }
}


class MatchingService:
    @staticmethod
    def calculate_role_relevance(job_title: str, candidate_roles: List[str]) -> Tuple[float, str]:
        """
        Calibrated semantic role relevance scoring.
        Returns (relevance_score: 0.0 - 1.0, role_diagnostic_text).
        Prevents unrelated roles (e.g. .NET / Frontend for AI/ML target) from scoring high.
        """
        if not job_title or not candidate_roles:
            return 0.3, "Candidate has no specified target roles."

        norm_title = job_title.lower().strip()
        best_score = 0.0
        best_explanation = "Low role relevance."

        # Identify candidate's target domains
        candidate_domains = set()
        for cr in candidate_roles:
            cr_lower = cr.lower()
            for domain, data in ROLE_CLUSTERS.items():
                if any(kw in cr_lower for kw in data["keywords"]):
                    candidate_domains.add(domain)

        for cr in candidate_roles:
            cr_lower = cr.lower().strip()

            # 1. Exact or Substring Match (e.g. "AI/ML Engineer" in "Senior AI/ML Engineer")
            if cr_lower in norm_title or norm_title in cr_lower:
                score = 0.95
                return score, f"Direct title match with candidate target role '{cr}'."

            # 2. Check acronym / variant expansions (e.g. "aiml", "ai/ml", "machine learning")
            is_aiml_target = any(k in cr_lower for k in ["aiml", "ai/ml", "ai / ml", "machine learning", "artificial intelligence"])
            is_aiml_job = any(k in norm_title for k in ["aiml", "ai/ml", "ai / ml", "machine learning", "artificial intelligence", "deep learning", "ai engineer", "ml engineer", "data scientist"])
            
            if is_aiml_target and is_aiml_job:
                # Both belong to AI/ML core
                score = 0.90
                return score, f"Strong semantic domain match between '{job_title}' and AI/ML target."

            # 3. Check domain cluster alignment
            job_domains = set()
            for domain, data in ROLE_CLUSTERS.items():
                if any(kw in norm_title for kw in data["keywords"]):
                    job_domains.add(domain)

            common_domains = candidate_domains.intersection(job_domains)
            if common_domains:
                score = 0.80
                return score, f"Role shares technical domain ({', '.join(common_domains)}) with candidate goals."

            # 4. General Software Engineer fallback (if candidate targeted general SWE)
            if "fullstack" in candidate_domains and ("software" in norm_title or "developer" in norm_title or "engineer" in norm_title):
                if 0.70 > best_score:
                    best_score = 0.70
                    best_explanation = "General software development role matches software engineering direction."

            # 5. Domain Conflict / Cross-Discipline
            # e.g., candidate wants AI/ML, but job is React Frontend Developer, .NET Developer, or Civil Engineer
            if "ai_ml" in candidate_domains:
                if any(k in norm_title for k in ["frontend", "react", "angular", ".net", "php", "civil", "mechanical", "wordpress", "sales", "hr", "recruiter", "mern"]):
                    if not is_aiml_job:
                        return 0.10, f"Role '{job_title}' is in a distinct technical track from candidate's AI/ML target."

        # If only a generic word like 'engineer' matched but domains didn't align
        if any(w in norm_title for w in ["engineer", "developer"]):
            if best_score == 0.0:
                best_score = 0.25
                best_explanation = f"Generic engineering title without domain alignment to candidate's targets ({', '.join(candidate_roles)})."
        else:
            if best_score == 0.0:
                best_score = 0.10
                best_explanation = f"Title '{job_title}' does not match candidate targets."

        return best_score, best_explanation

    @staticmethod
    def match_job(
        job: NormalizedJob,
        candidate_intel: CandidateIntelligenceRepresentation,
        preferred_locations: List[str],
        remote_preference: str,
        experience_level: str
    ) -> Dict[str, Any]:
        """
        Explainable heuristic scoring of an advertised job against candidate intelligence.
        Uses calibrated gates to prevent unrelated roles from receiving high scores.
        """
        verified_skill_names = {s.name.lower() for s in candidate_intel.verified_skills}
        inferred_skill_names = {s.name.lower() for s in candidate_intel.inferred_skills}

        # 1. Role Title Relevance (Calibrated Gate)
        candidate_target_roles = [d.target_role for d in candidate_intel.career_directions]
        if not candidate_target_roles and candidate_intel.preferences.get("desired_roles"):
            candidate_target_roles = candidate_intel.preferences["desired_roles"]
        if not candidate_target_roles:
            candidate_target_roles = ["Software Engineer"]

        role_score, role_explanation = MatchingService.calculate_role_relevance(job.title, candidate_target_roles)

        # 2. Skill Requirements Matching
        job_skills = [s.lower() for s in job.extracted_skills]
        matched: List[str] = []
        missing: List[str] = []

        if job_skills:
            for s in job_skills:
                if s in verified_skill_names:
                    matched.append(s.title())
                elif s in inferred_skill_names:
                    matched.append(f"{s.title()} (Inferred)")
                else:
                    missing.append(s.title())
            
            # Require at least 3 skills to reach 100% skill match (prevents 1 skill = 100% inflation)
            effective_denominator = max(len(job_skills), 3)
            skill_score = min(1.0, len(matched) / effective_denominator)
        else:
            # If no skills listed in metadata, analyze description text directly
            text = (job.title + " " + (job.description or "")).lower()
            matched_from_text = [
                s.name for s in candidate_intel.verified_skills if s.name.lower() in text
            ]
            matched = matched_from_text[:6]
            skill_score = min(0.80, len(matched) * 0.20) if matched else 0.25

        # 3. Work Arrangement & Location Compatibility
        loc_score = 0.85
        critical_failures: List[str] = []

        job_loc = (job.location or "").lower()
        if remote_preference == "remote" and not job.is_remote and job.work_arrangement == "onsite":
            loc_score = 0.30
            if preferred_locations and not any(pl.lower() in job_loc for pl in preferred_locations):
                critical_failures.append("Candidate requires remote work, but opening is strictly on-site.")
        elif preferred_locations:
            if any(pl.lower() in job_loc for pl in preferred_locations) or job.is_remote:
                loc_score = 1.0
            else:
                loc_score = 0.70

        # 4. Experience Level Check
        title_lower = job.title.lower()
        exp_score = 0.85
        if any(w in title_lower for w in ["senior", "lead", "staff", "principal"]):
            if experience_level == "entry":
                critical_failures.append("Role mandates Senior/Staff leadership while candidate profile indicates Entry level.")
                exp_score = 0.20

        # 5. Composite Score with STRICT Relevance Gating
        # Standard weights: Role Relevance 45%, Skills 35%, Location/Arrangement 20%
        raw_composite = (role_score * 0.45) + (skill_score * 0.35) + (loc_score * 0.20)

        # CALIBRATION GATE:
        # If the role has low relevance to candidate's goal, CAP the total score!
        # An unrelated job (e.g. .NET Fresher or MERN Developer when seeking AI/ML)
        # must never receive an attractive score like 81%!
        if role_score < 0.30:
            match_score = min(raw_composite, role_score * 1.1, 0.30)
        elif role_score < 0.50:
            match_score = min(raw_composite, 0.45)
        else:
            match_score = raw_composite

        match_score = round(min(1.0, max(0.0, match_score)), 2)

        # 6. Action Recommendation
        if critical_failures or match_score < settings.MATCH_IMPROVE_FIRST_THRESHOLD or role_score < 0.40:
            action = RecommendedAction.SKIP
        elif match_score >= settings.MATCH_CONTACT_NOW_THRESHOLD and role_score >= 0.70:
            action = RecommendedAction.CONTACT_NOW
        else:
            action = RecommendedAction.IMPROVE_FIRST

        # 7. Transparent, grounded explanation
        explanation = (
            f"Candidate Fit: {int(match_score * 100)}% | Role Relevance: {int(role_score * 100)}%. "
            f"{role_explanation} "
            f"Matched {len(matched)} skill(s) ({', '.join(matched[:3]) if matched else 'None'}). "
            f"{f'Missing skills: {', '.join(missing[:3])}. ' if missing else ''}"
            f"Work arrangement: {job.work_arrangement.capitalize()}."
        )

        # Evidence confidence: penalize missing URL or generic aggregator
        evidence_conf = float(job.confidence)
        if not job.description or len(job.description.strip()) < 50:
            evidence_conf = min(evidence_conf, 0.60)

        return {
            "match_score": match_score,
            "matched_skills": matched,
            "missing_skills": missing,
            "critical_failures": critical_failures,
            "recommended_action": action,
            "evidence_confidence": round(evidence_conf, 2),
            "explanation": explanation
        }

    @staticmethod
    def match_company(
        company: NormalizedCompany,
        candidate_intel: CandidateIntelligenceRepresentation,
        evaluation: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Scores unadvertised companies for proactive value outreach.
        """
        align_score = evaluation["alignment_score"]
        growth_score = evaluation["growth_signal_score"]
        opp_type = evaluation["opportunity_type"]

        # Composite match score: 60% alignment, 40% growth signals
        raw_score = (align_score * 0.60) + (growth_score * 0.40)
        match_score = round(min(1.0, max(0.0, raw_score)), 2)

        if opp_type == OpportunityType.EMERGING and match_score >= 0.65:
            action = RecommendedAction.CONTACT_NOW
        elif opp_type == OpportunityType.STRATEGIC and match_score >= 0.50:
            action = RecommendedAction.IMPROVE_FIRST
        elif match_score < 0.40:
            action = RecommendedAction.SKIP
        else:
            action = RecommendedAction.IMPROVE_FIRST

        explanation = (
            f"Unadvertised Opportunity ({opp_type.value}). "
            f"Candidate-Company alignment: {int(align_score * 100)}%. "
            f"Verified growth signal score: {int(growth_score * 100)}%. "
            f"Calibrated strategic score: {int(match_score * 100)}%."
        )

        return {
            "match_score": match_score,
            "matched_skills": evaluation.get("matched_skills", []),
            "missing_skills": [],
            "critical_failures": [],
            "recommended_action": action,
            "evidence_confidence": round(float(company.confidence), 2),
            "explanation": explanation
        }
