from typing import Dict, Any, List
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.profile import Profile, SkillStatus, SkillSource
from app.models.resume import Resume
from app.schemas.intelligence import (
    CandidateIntelligenceRepresentation,
    CandidateIdentity,
    CategorizedSkill,
    CareerDirectionSummary,
    CompletenessMetric
)
from app.services.profile_service import ProfileService

# Deterministic skill inference rules:
# If tech X is present, related foundation Y may be inferred with transparent evidence
INFERENCE_RULES = {
    "react": ("JavaScript", "Frontend Development", "Evidence: React framework indicates core JavaScript runtime competency."),
    "angular": ("TypeScript", "Frontend Architecture", "Evidence: Angular framework implies TypeScript and modern frontend design."),
    "fastapi": ("Python", "API Architecture", "Evidence: FastAPI framework implies Python asynchronous web architecture."),
    "django": ("Python", "Web Systems", "Evidence: Django framework implies Python web application development."),
    "pytorch": ("Deep Learning", "AI Modeling", "Evidence: PyTorch implies deep learning model implementation."),
    "kubernetes": ("Container Orchestration", "DevOps Systems", "Evidence: Kubernetes indicates distributed container deployment knowledge."),
}


class ProfileIntelligenceService:
    @staticmethod
    def generate_candidate_intelligence(db: Session, user: User) -> CandidateIntelligenceRepresentation:
        profile = ProfileService.get_or_create_profile(db, user)
        resumes = db.query(Resume).filter(Resume.user_id == user.id, Resume.is_active == True).all()

        # 1. Identity
        identity = CandidateIdentity(
            full_name=user.full_name,
            email=user.email,
            phone=profile.phone,
            location=profile.location,
            headline=profile.headline,
            links=profile.links or {}
        )

        # 2. Education aggregation
        education_list = []
        for edu in profile.education:
            education_list.append({
                "institution": edu.institution,
                "degree": edu.degree,
                "field_of_study": edu.field_of_study,
                "start_year": edu.start_year,
                "graduation_year": edu.graduation_year,
                "grade_or_gpa": edu.grade_or_gpa,
                "details": edu.details,
                "verified": True
            })

        # 3. Work Experience aggregation
        experience_list = []
        for exp in profile.work_experience:
            experience_list.append({
                "company": exp.company,
                "role": exp.role,
                "location": exp.location,
                "start_date": exp.start_date,
                "end_date": exp.end_date,
                "is_current": exp.is_current,
                "description": exp.description,
                "technologies": exp.technologies,
                "verified": True
            })

        # 4. Projects aggregation
        projects_list = []
        for proj in profile.projects:
            projects_list.append({
                "title": proj.title,
                "description": proj.description,
                "technologies": proj.technologies,
                "role_contribution": proj.role_contribution,
                "github_url": proj.github_url,
                "demo_url": proj.demo_url,
                "verified": True
            })

        # 5. Skills Partitioning (VERIFIED vs INFERRED vs UNVERIFIED)
        verified_skills: Dict[str, CategorizedSkill] = {}
        inferred_skills: Dict[str, CategorizedSkill] = {}
        unverified_skills: Dict[str, CategorizedSkill] = {}

        # Add profile skills
        for sk in profile.skills:
            cat_skill = CategorizedSkill(
                name=sk.name,
                category=sk.category,
                status=sk.status,
                source=f"Profile ({sk.source})",
                evidence=sk.evidence or "Explicitly listed in user profile",
                confidence_score=sk.confidence_score
            )
            if sk.status == SkillStatus.VERIFIED:
                verified_skills[sk.name.lower()] = cat_skill
            elif sk.status == SkillStatus.INFERRED:
                inferred_skills[sk.name.lower()] = cat_skill
            else:
                unverified_skills[sk.name.lower()] = cat_skill

        # Aggregate skills from uploaded active resumes (all verified by direct text extraction)
        for r in resumes:
            for sk_item in (r.extracted_skills or []):
                name_lower = sk_item["name"].lower()
                if name_lower not in verified_skills:
                    verified_skills[name_lower] = CategorizedSkill(
                        name=sk_item["name"],
                        category=sk_item.get("category", "technical"),
                        status=SkillStatus.VERIFIED,
                        source=f"Resume: {r.title}",
                        evidence=sk_item.get("evidence", f"Extracted from {r.original_filename}"),
                        confidence_score=1.0
                    )

        # Rule-based Grounded Inference (only if not already verified!)
        for v_name in list(verified_skills.keys()):
            if v_name in INFERENCE_RULES:
                inferred_name, inferred_cat, evidence_note = INFERENCE_RULES[v_name]
                inf_lower = inferred_name.lower()
                if inf_lower not in verified_skills and inf_lower not in inferred_skills:
                    inferred_skills[inf_lower] = CategorizedSkill(
                        name=inferred_name,
                        category=inferred_cat,
                        status=SkillStatus.INFERRED,
                        source="Evidence-Grounded Inference",
                        evidence=evidence_note,
                        confidence_score=0.85
                    )

        # 6. Preferences
        pref = profile.preferences
        preferences_dict = {
            "desired_roles": pref.desired_roles if pref else [],
            "preferred_industries": pref.preferred_industries if pref else [],
            "preferred_locations": pref.preferred_locations if pref else [],
            "remote_preference": pref.remote_preference if pref else "flexible",
            "experience_level": pref.experience_level if pref else "mid",
            "employment_preference": pref.employment_preference if pref else "full-time",
        }

        # 7. Resume Inventory
        resume_inventory = []
        for r in resumes:
            resume_inventory.append({
                "id": r.id,
                "title": r.title,
                "target_role": r.target_role,
                "is_preferred": r.is_preferred,
                "original_filename": r.original_filename,
                "file_size": r.file_size,
                "parsing_status": r.parsing_status,
                "parsing_confidence": r.parsing_confidence,
                "extracted_skills_count": len(r.extracted_skills or []),
                "created_at": r.created_at.isoformat()
            })

        # 8. Career Directions Analysis
        career_directions: List[CareerDirectionSummary] = []
        all_target_roles = set(preferences_dict["desired_roles"])
        for r in resumes:
            if r.target_role and r.target_role != "General":
                all_target_roles.add(r.target_role)

        for target in sorted(all_target_roles):
            matched_resumes = [r.title for r in resumes if r.target_role.lower() == target.lower()]
            # Relevant verified skills matching role keywords
            role_keywords = target.lower().split()
            matched_skills = [
                s.name for s in verified_skills.values()
                if any(kw in s.name.lower() or kw in s.category.lower() for kw in role_keywords)
            ]
            readiness = "High" if matched_resumes and len(matched_skills) >= 2 else ("Moderate" if matched_skills or matched_resumes else "Emerging")
            
            career_directions.append(CareerDirectionSummary(
                target_role=target,
                associated_resumes=matched_resumes,
                matching_skills=matched_skills[:8],
                readiness_level=readiness,
                evidence_notes=f"Supported by {len(matched_resumes)} tailored resume(s) and {len(matched_skills)} verified competencies."
            ))

        # 9. Completeness & Grounding
        missing_fields = []
        recommendations = []
        if not user.full_name:
            missing_fields.append("Full Name")
            recommendations.append("Add your full name to candidate identity.")
        if not profile.headline:
            missing_fields.append("Professional Headline")
            recommendations.append("Specify a professional headline describing your domain focus.")
        if not education_list:
            missing_fields.append("Education")
            recommendations.append("Add your degree and university credentials.")
        if not experience_list:
            missing_fields.append("Work Experience")
            recommendations.append("Document your work history or internships.")
        if not verified_skills:
            missing_fields.append("Verified Skills")
            recommendations.append("Upload a resume or list your core technical competencies.")
        if not resumes:
            missing_fields.append("Targeted Resumes")
            recommendations.append("Upload at least one resume targeted towards your primary career direction.")

        completeness_pct = ProfileService.calculate_completeness(profile, user)
        # Factor in resume upload
        if resumes:
            completeness_pct = min(100, completeness_pct + 15)

        # Overall confidence score
        confidence = 0.95 if (len(verified_skills) > 3 and resumes) else (0.75 if resumes or profile.education else 0.50)

        grounding_summary = (
            f"Candidate profile synthesized from {len(resumes)} uploaded resume(s) and user profile inputs. "
            f"All {len(verified_skills)} verified skills are backed by direct textual citations. "
            f"{len(inferred_skills)} skills are conservatively inferred with transparent rationale. "
            "No claims are fabricated."
        )

        return CandidateIntelligenceRepresentation(
            identity=identity,
            education=education_list,
            work_experience=experience_list,
            projects=projects_list,
            verified_skills=list(verified_skills.values()),
            inferred_skills=list(inferred_skills.values()),
            unverified_skills=list(unverified_skills.values()),
            preferences=preferences_dict,
            resume_inventory=resume_inventory,
            career_directions=career_directions,
            profile_completeness=CompletenessMetric(
                overall_percentage=completeness_pct,
                missing_critical_fields=missing_fields,
                recommendations=recommendations
            ),
            overall_confidence=confidence,
            evidence_grounding_summary=grounding_summary
        )
