from typing import Dict, Any, List, Optional, Set
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.profile import Profile, SkillStatus
from app.models.resume import Resume
from app.models.opportunity import Opportunity, Evidence
from app.models.job import Job
from app.models.company import Company
from app.services.cosgo_optimizer import CosgoOptimizer


class OutreachContextBuilder:
    """
    Builds an explicit, evidence-grounded context object for personalized AI outreach.
    Enforces truthfulness: extracts strictly persisted candidate details and job evidence,
    distinguishing verified skills from inferred skills, and flagging job status uncertainty.
    """

    @staticmethod
    def build_context(
        db: Session,
        user_id: str,
        opportunity_id: Optional[str] = None,
        resume_id: Optional[str] = None,
        recipient_name: Optional[str] = None,
        recipient_role: Optional[str] = None,
        purpose: str = "full_time_application",
        recipient_type: str = "hiring_manager",
        existing_snapshot: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Extracts and correlates real data from candidate profile, resume, and opportunity.
        Returns a structured dictionary suitable for prompting the LLM and saving as an immutable snapshot.
        """
        # 1. Fetch User and Profile
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")

        profile = db.query(Profile).filter(Profile.user_id == user_id).first()

        candidate_name = user.full_name or (user.email.split("@")[0].replace(".", " ").title() if user.email else "Candidate")
        contact_email = user.email
        phone = profile.phone if profile else None
        location = profile.location if profile else None
        headline = profile.headline if profile else None
        bio = profile.bio if profile else None
        links = profile.links if profile and profile.links else {}

        # Skills breakdown
        verified_skills: List[str] = []
        inferred_skills: List[str] = []
        if profile and profile.skills:
            for s in profile.skills:
                canon = CosgoOptimizer.normalize_skill_name(s.name)
                if s.status == SkillStatus.VERIFIED or s.status == "VERIFIED":
                    verified_skills.append(canon)
                elif s.status == SkillStatus.INFERRED or s.status == "INFERRED":
                    inferred_skills.append(canon)

        # Remove duplicates preserving order
        verified_skills = list(dict.fromkeys(verified_skills))
        inferred_skills = [s for s in list(dict.fromkeys(inferred_skills)) if s not in verified_skills]

        # Projects
        candidate_projects: List[Dict[str, Any]] = []
        if profile and profile.projects:
            for p in profile.projects:
                candidate_projects.append({
                    "title": p.title,
                    "description": p.description or "",
                    "technologies": [CosgoOptimizer.normalize_skill_name(t) for t in (p.technologies or [])],
                    "role_contribution": p.role_contribution or "",
                    "github_url": p.github_url or "",
                    "demo_url": p.demo_url or ""
                })

        # Experience
        candidate_experience: List[Dict[str, Any]] = []
        if profile and profile.work_experience:
            for exp in profile.work_experience:
                candidate_experience.append({
                    "company": exp.company,
                    "role": exp.role,
                    "location": exp.location or "",
                    "start_date": exp.start_date or "",
                    "end_date": exp.end_date or ("Present" if exp.is_current else ""),
                    "is_current": exp.is_current,
                    "description": exp.description or "",
                    "technologies": [CosgoOptimizer.normalize_skill_name(t) for t in (exp.technologies or [])]
                })

        # Education
        candidate_education: List[Dict[str, Any]] = []
        if profile and profile.education:
            for edu in profile.education:
                candidate_education.append({
                    "institution": edu.institution,
                    "degree": edu.degree,
                    "field_of_study": edu.field_of_study or "",
                    "graduation_year": edu.graduation_year,
                    "grade_or_gpa": edu.grade_or_gpa or ""
                })

        # 2. Selected Resume (if any)
        resume_info: Optional[Dict[str, Any]] = None
        if resume_id:
            resume = db.query(Resume).filter(Resume.id == resume_id, Resume.user_id == user_id).first()
            if resume:
                resume_info = {
                    "id": resume.id,
                    "title": resume.title,
                    "target_role": resume.target_role,
                    "extracted_skills": [CosgoOptimizer.normalize_skill_name(s) for s in (resume.extracted_skills or [])],
                    "extracted_projects": resume.extracted_projects or [],
                    "extracted_experience": resume.extracted_experience or [],
                    "extracted_education": resume.extracted_education or []
                }
                # If profile was sparse, merge resume skills into verified skills if not already present
                for rs in resume_info["extracted_skills"]:
                    if rs not in verified_skills and rs not in inferred_skills:
                        verified_skills.append(rs)

        # 3. Fetch Opportunity, Job, Company, and Evidence
        opportunity = (
            db.query(Opportunity).filter(Opportunity.id == opportunity_id, Opportunity.user_id == user_id).first()
            if opportunity_id else None
        )

        job_snapshot = existing_snapshot.get("job", {}) if existing_snapshot else {}
        company_snapshot = existing_snapshot.get("company", {}) if existing_snapshot else {}

        if opportunity:
            job = db.query(Job).filter(Job.id == opportunity.job_id).first() if opportunity.job_id else None
            company = db.query(Company).filter(Company.id == opportunity.company_id).first() if opportunity.company_id else None

            job_title = job.title if job else "Software Engineer"
            company_name = job.company_name if job else (company.name if company else "Hiring Company")
            job_location = job.location if job else "Not specified"
            work_arrangement = job.work_arrangement if job else "flexible"
            employment_type = job.employment_type if job else "full-time"
            primary_url = job.primary_url if job else ""
            application_url = job.application_url if job else primary_url
            is_verified_opening = job.is_verified if job else False
            verification_status = job.verification_status if job else "LISTING_FOUND_STATUS_UNVERIFIED"
            job_description = (job.description or "")[:2000] if job else ""

            # Requirements
            raw_reqs: Set[str] = set()
            if job and job.requirements:
                for r in job.requirements:
                    raw_reqs.add(CosgoOptimizer.normalize_skill_name(r.description))
            if opportunity.matched_skills:
                for s in opportunity.matched_skills:
                    raw_reqs.add(CosgoOptimizer.normalize_skill_name(s))
            if opportunity.missing_skills:
                for s in opportunity.missing_skills:
                    raw_reqs.add(CosgoOptimizer.normalize_skill_name(s))

            requirements_list = sorted(list(raw_reqs))

            # Company intelligence
            company_classification = company.classification if company else "Unspecified"
            company_description = (company.description or "")[:600] if company else ""
            company_website = getattr(company, "website_url", getattr(company, "website", "")) if company else ""

            # Evidence claims observed from web research
            evidence_items: List[str] = []
            if opportunity.evidence_items:
                for ev in opportunity.evidence_items[:5]:
                    if ev.claim_text:
                        evidence_items.append(ev.claim_text.strip())
        elif job_snapshot:
            # Fall back to historical snapshot when opportunity was deleted or detached
            job_title = job_snapshot.get("title", "Software Engineer")
            company_name = job_snapshot.get("company_name", company_snapshot.get("name", "Hiring Company"))
            job_location = job_snapshot.get("location", "Not specified")
            work_arrangement = job_snapshot.get("work_arrangement", "flexible")
            employment_type = job_snapshot.get("employment_type", "full-time")
            primary_url = job_snapshot.get("primary_url", "")
            application_url = job_snapshot.get("application_url", primary_url)
            is_verified_opening = job_snapshot.get("is_verified", False)
            verification_status = job_snapshot.get("verification_status", "HISTORICAL_SNAPSHOT")
            job_description = job_snapshot.get("description", "")
            requirements_list = job_snapshot.get("requirements", [])
            company_classification = company_snapshot.get("classification", "Unspecified")
            company_description = company_snapshot.get("overview", "")
            company_website = company_snapshot.get("website_url", "")
            evidence_items = existing_snapshot.get("evidence", [])
        else:
            raise ValueError(f"Opportunity {opportunity_id} not found and no historical snapshot available.")

        # Check status uncertainty (e.g. EXPIRED_OR_CLOSED or unverified)
        is_uncertain_or_closed = (
            "CLOSED" in verification_status.upper()
            or "EXPIRED" in verification_status.upper()
            or not is_verified_opening
        )

        # 4. Alignment / Relevance Selection
        # Identify candidate's verified skills that directly match this job's requirements
        job_reqs_lower = {r.lower() for r in requirements_list}
        matching_verified_skills = [s for s in verified_skills if s.lower() in job_reqs_lower]

        # If matching skills is empty, select top verified skills
        highlight_skills = matching_verified_skills if matching_verified_skills else verified_skills[:4]

        # Select 1-2 most relevant candidate projects
        scored_projects: List[tuple] = []
        for p in candidate_projects:
            p_tech_lower = {t.lower() for t in p.get("technologies", [])}
            overlap = len(p_tech_lower.intersection(job_reqs_lower))
            scored_projects.append((overlap, p))
        scored_projects.sort(key=lambda x: x[0], reverse=True)
        relevant_projects = [p for _, p in scored_projects[:2]]

        # Select most relevant work experience
        scored_experience: List[tuple] = []
        for exp in candidate_experience:
            e_tech_lower = {t.lower() for t in exp.get("technologies", [])}
            overlap = len(e_tech_lower.intersection(job_reqs_lower))
            scored_experience.append((overlap, exp))
        scored_experience.sort(key=lambda x: x[0], reverse=True)
        relevant_experience = [exp for _, exp in scored_experience[:2]]

        # Construct Context Dictionary
        return {
            "candidate": {
                "name": candidate_name,
                "email": contact_email,
                "phone": phone,
                "location": location,
                "headline": headline,
                "bio": bio,
                "links": links,
                "verified_skills": verified_skills,
                "inferred_skills": inferred_skills,
                "highlight_skills": highlight_skills,
                "relevant_projects": relevant_projects,
                "relevant_experience": relevant_experience,
                "education": candidate_education[:2]
            },
            "job": {
                "title": job_title,
                "company_name": company_name,
                "location": job_location,
                "work_arrangement": work_arrangement,
                "employment_type": employment_type,
                "requirements": requirements_list,
                "matching_skills_count": len(matching_verified_skills),
                "primary_url": primary_url,
                "application_url": application_url,
                "is_verified_opening": is_verified_opening,
                "verification_status": verification_status,
                "is_uncertain_or_closed": is_uncertain_or_closed,
                "description_excerpt": job_description[:1000] if job_description else None,
                "company_classification": company_classification,
                "company_description": company_description,
                "company_website": company_website,
                "evidence_claims": evidence_items
            },
            "outreach_parameters": {
                "purpose": purpose,
                "recipient_type": recipient_type,
                "recipient_name": (recipient_name or "").strip() or None,
                "recipient_role": (recipient_role or "").strip() or None
            },
            "resume_context": {
                "resume_id": resume_info.get("id") if resume_info else None,
                "resume_title": resume_info.get("title") if resume_info else None,
                "target_role": resume_info.get("target_role") if resume_info else None
            } if resume_info else None
        }
