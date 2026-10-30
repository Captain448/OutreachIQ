import math
import re
from typing import List, Dict, Any, Optional, Set
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy import desc

from app.models.user import User
from app.models.profile import Profile, Skill, Project, Preferences, SkillStatus
from app.models.resume import Resume
from app.models.cosgo import CosgoRun, CosgoAction, CosgoProgressState
from app.models.learning import UserLearningPlan
from app.services.cosgo_service import CosgoService
from app.services.learning.doc_catalog import DocCatalogService, DocResource
from app.services.learning.course_catalog import CourseCatalogService, CourseItem
from app.services.learning.certification_directory import CertificationDirectoryService, CertificationEntry
from app.services.learning.project_recommender import ProjectRecommenderService, ProjectBlueprint
from app.services.learning.skill_curriculum import SkillCurriculumService
from app.services.providers.youtube_adapter import YouTubeAdapter
from app.services.resume_parser import KNOWN_SKILLS


# Canonical role-to-skill requirements matrix for initial gap inference when COSGO run is not yet triggered
ROLE_CORE_SKILLS: Dict[str, Dict[str, Any]] = {
    "backend": {
        "required": ["Python", "FastAPI", "PostgreSQL", "Docker"],
        "optional": ["Redis", "CI/CD", "Kubernetes", "Linux"],
        "hours": {"Python": 18.0, "FastAPI": 14.0, "PostgreSQL": 16.0, "Docker": 14.0, "Redis": 8.0, "CI/CD": 10.0, "Kubernetes": 20.0, "Linux": 12.0}
    },
    "frontend": {
        "required": ["TypeScript", "Angular", "JavaScript"],
        "optional": ["HTML/CSS", "Tailwind CSS", "CI/CD"],
        "hours": {"TypeScript": 14.0, "Angular": 22.0, "JavaScript": 14.0, "HTML/CSS": 8.0, "Tailwind CSS": 6.0, "CI/CD": 10.0}
    },
    "full stack": {
        "required": ["Python", "FastAPI", "TypeScript", "Angular", "PostgreSQL"],
        "optional": ["Docker", "Redis", "CI/CD"],
        "hours": {"Python": 18.0, "FastAPI": 14.0, "TypeScript": 14.0, "Angular": 22.0, "PostgreSQL": 16.0, "Docker": 14.0, "Redis": 8.0, "CI/CD": 10.0}
    },
    "devops": {
        "required": ["Docker", "Kubernetes", "Linux", "CI/CD"],
        "optional": ["Terraform", "AWS", "Python"],
        "hours": {"Docker": 14.0, "Kubernetes": 20.0, "Linux": 12.0, "CI/CD": 10.0, "Terraform": 14.0, "AWS": 22.0, "Python": 18.0}
    },
    "machine learning": {
        "required": ["Python", "Scikit-Learn", "SQL"],
        "optional": ["PyTorch", "FastAPI", "Docker"],
        "hours": {"Python": 18.0, "Scikit-Learn": 18.0, "SQL": 12.0, "PyTorch": 24.0, "FastAPI": 14.0, "Docker": 14.0}
    }
}

SKILL_PREREQUISITES: Dict[str, List[str]] = {
    "fastapi": ["Python"],
    "django": ["Python"],
    "flask": ["Python"],
    "angular": ["TypeScript", "JavaScript"],
    "react": ["JavaScript"],
    "kubernetes": ["Docker", "Linux"],
    "terraform": ["Cloud Basics"],
    "pytorch": ["Python"],
    "scikit-learn": ["Python"]
}


class LearningPlanService:
    @classmethod
    def get_or_create_user_plan(cls, user_id: str, db: Session) -> UserLearningPlan:
        plan = db.query(UserLearningPlan).filter(UserLearningPlan.user_id == user_id).first()
        if not plan:
            plan = UserLearningPlan(
                user_id=user_id,
                weekly_hours_budget=10.0,
                completed_skills=[],
                bookmarked_resources=[],
                project_progress={}
            )
            db.add(plan)
            db.commit()
            db.refresh(plan)
        return plan

    @classmethod
    def update_weekly_budget(cls, user_id: str, weekly_hours: float, db: Session) -> UserLearningPlan:
        plan = cls.get_or_create_user_plan(user_id, db)
        plan.weekly_hours_budget = max(2.0, min(60.0, float(weekly_hours)))
        db.commit()
        db.refresh(plan)
        return plan

    @classmethod
    def gather_candidate_facts(cls, user_id: str, db: Session) -> Dict[str, Any]:
        """
        Gathers grounded candidate profile, work experience, uploaded resumes,
        and target roles. Safely extracts skills and projects across all sources.
        Gracefully handles missing, empty, or unparsed resumes without inventing facts.
        """
        profile = db.query(Profile).filter(Profile.user_id == user_id).first()
        resumes = db.query(Resume).filter(Resume.user_id == user_id).all()

        candidate_skills: Set[str] = set()
        existing_projects: List[Dict[str, Any]] = []
        candidate_experience: List[Dict[str, Any]] = []
        target_roles: List[str] = []

        # 1. Facts from Candidate Profile
        if profile:
            if profile.skills:
                for s in profile.skills:
                    if s and getattr(s, "name", None):
                        candidate_skills.add(s.name.strip())

            if profile.projects:
                for p in profile.projects:
                    if p and getattr(p, "title", None):
                        existing_projects.append({
                            "title": p.title.strip(),
                            "description": getattr(p, "description", "") or "",
                            "technologies": getattr(p, "technologies", []) or []
                        })

            if getattr(profile, "work_experience", None):
                for exp in profile.work_experience:
                    if exp:
                        exp_role = getattr(exp, "role", "") or ""
                        exp_comp = getattr(exp, "company", "") or ""
                        exp_desc = getattr(exp, "description", "") or ""
                        if exp_role or exp_comp:
                            candidate_experience.append({
                                "role": exp_role.strip(),
                                "company": exp_comp.strip(),
                                "description": exp_desc.strip(),
                                "technologies": getattr(exp, "technologies", []) or []
                            })

            if profile.preferences and profile.preferences.desired_roles:
                for r_name in profile.preferences.desired_roles:
                    if isinstance(r_name, str) and r_name.strip():
                        target_roles.append(r_name.strip())

        # 2. Facts from Uploaded Resumes (using actual SQLAlchemy Resume model fields)
        for r in resumes:
            # A. Skills extraction from resume
            raw_skills = getattr(r, "extracted_skills", None)
            if raw_skills and isinstance(raw_skills, list):
                for item in raw_skills:
                    if isinstance(item, dict):
                        skill_name = item.get("name") or item.get("skill") or item.get("title")
                        if skill_name and isinstance(skill_name, str) and skill_name.strip():
                            candidate_skills.add(skill_name.strip())
                    elif isinstance(item, str) and item.strip():
                        candidate_skills.add(item.strip())

            # Fallback text scan if extracted_skills was empty but parsed_text exists
            if not raw_skills and getattr(r, "parsed_text", None):
                lower_text = str(r.parsed_text).lower()
                for skill_kw in KNOWN_SKILLS:
                    pattern = r"\b" + re.escape(skill_kw) + r"\b"
                    if re.search(pattern, lower_text):
                        display_name = skill_kw.title() if len(skill_kw) > 3 else skill_kw.upper()
                        if skill_kw in ["fastapi", "next.js", "node.js"]:
                            display_name = skill_kw
                        elif skill_kw == "ci/cd":
                            display_name = "CI/CD"
                        candidate_skills.add(display_name)

            # B. Projects extraction from resume
            raw_projects = getattr(r, "extracted_projects", None)
            if raw_projects and isinstance(raw_projects, list):
                for proj in raw_projects:
                    if isinstance(proj, dict):
                        p_title = proj.get("title") or proj.get("name") or proj.get("raw_entry") or ""
                        p_desc = proj.get("description") or proj.get("raw_entry") or ""
                        p_techs = proj.get("technologies") or []
                        if p_title and str(p_title).strip():
                            existing_projects.append({
                                "title": str(p_title).strip(),
                                "description": str(p_desc).strip(),
                                "technologies": p_techs if isinstance(p_techs, list) else []
                            })
                    elif isinstance(proj, str) and proj.strip():
                        existing_projects.append({
                            "title": proj.strip(),
                            "description": proj.strip(),
                            "technologies": []
                        })

            # C. Experience extraction from resume
            raw_exp = getattr(r, "extracted_experience", None)
            if raw_exp and isinstance(raw_exp, list):
                for exp in raw_exp:
                    if isinstance(exp, dict):
                        e_role = exp.get("role") or exp.get("title") or exp.get("raw_entry") or ""
                        e_comp = exp.get("company") or ""
                        e_desc = exp.get("description") or exp.get("raw_entry") or ""
                        if e_role and str(e_role).strip():
                            candidate_experience.append({
                                "role": str(e_role).strip(),
                                "company": str(e_comp).strip(),
                                "description": str(e_desc).strip(),
                                "technologies": exp.get("technologies") or []
                            })
                    elif isinstance(exp, str) and exp.strip():
                        candidate_experience.append({
                            "role": exp.strip(),
                            "company": "",
                            "description": exp.strip(),
                            "technologies": []
                        })

            # D. Role preference from resume if target_roles is still unconfigured
            resume_target_role = getattr(r, "target_role", None)
            if resume_target_role and isinstance(resume_target_role, str) and resume_target_role.strip():
                clean_role = resume_target_role.strip()
                if clean_role.lower() not in ["general", "none", "unknown", ""]:
                    if clean_role not in target_roles:
                        target_roles.append(clean_role)

        # Infer target role from experience if still unconfigured
        if not target_roles and candidate_experience:
            for exp in candidate_experience:
                role_text = exp.get("role", "").lower()
                for standard_role in [
                    "Backend Developer",
                    "Frontend Developer",
                    "Full Stack Developer",
                    "Software Engineer",
                    "DevOps Engineer",
                    "Machine Learning Engineer"
                ]:
                    if standard_role.lower() in role_text or any(w in role_text for w in standard_role.lower().split() if len(w) > 3):
                        if standard_role not in target_roles:
                            target_roles.append(standard_role)
                        break
                if target_roles:
                    break

        return {
            "candidate_skills": candidate_skills,
            "existing_projects": existing_projects,
            "candidate_experience": candidate_experience,
            "target_roles": target_roles,
            "resumes_count": len(resumes)
        }

    @classmethod
    async def build_personalized_learning_overview(
        cls,
        user_id: str,
        db: Session,
        include_youtube: bool = True
    ) -> Dict[str, Any]:
        """
        Synthesizes candidate profile, resumes, COSGO skill gaps, and target roles
        into an actionable, personalized learning dashboard and time-budgeted roadmap.
        Distinguishes source-verified facts from system inferences.
        """
        plan = cls.get_or_create_user_plan(user_id, db)
        facts = cls.gather_candidate_facts(user_id, db)

        candidate_skills = facts["candidate_skills"]
        existing_projects = facts["existing_projects"]
        candidate_experience = facts["candidate_experience"]
        target_roles = facts["target_roles"]
        resumes_count = facts["resumes_count"]

        # Onboarding / Empty State Detection
        # If candidate has zero skills, zero target roles, and zero uploaded resumes, return guided onboarding state
        if len(candidate_skills) == 0 and len(target_roles) == 0 and resumes_count == 0:
            return {
                "is_onboarding_empty_state": True,
                "message": "Welcome to OutReachIQ Learning & Projects! Add your desired roles in Profile Preferences or upload a resume to unlock personalized learning plans, documentation catalogs, and project blueprints.",
                "weekly_hours_budget": plan.weekly_hours_budget,
                "recommended_skills": [],
                "learning_phases": [],
                "recommended_projects": [],
                "candidate_experience": [],
                "catalog_overview": {
                    "total_documentation_pages": len(DocCatalogService.get_all_documentation()),
                    "total_verified_courses": len(CourseCatalogService.get_all_courses()),
                    "total_certifications": len(CertificationDirectoryService.get_all_certifications())
                }
            }

        # Default role fallback if none specified
        if not target_roles:
            target_roles = ["Software Engineer", "Backend Developer"]

        # 3. Extract Skill Gaps from COSGO or Domain Rules
        skill_gaps: List[Dict[str, Any]] = []
        addressed_skill_names: Set[str] = set()

        # Check latest COSGO run
        latest_cosgo = (
            db.query(CosgoRun)
            .filter(CosgoRun.user_id == user_id)
            .order_by(desc(CosgoRun.created_at))
            .first()
        )

        if latest_cosgo and latest_cosgo.actions:
            for action in latest_cosgo.actions:
                s_name = action.skill_name
                addressed_skill_names.add(s_name.lower())
                skill_gaps.append({
                    "skill_name": s_name,
                    "category": action.category,
                    "estimated_hours": float(action.estimated_hours),
                    "is_estimate": True,
                    "prerequisites": action.prerequisites or [],
                    "priority_rank": action.priority_rank,
                    "marginal_gain": action.marginal_coverage_gain,
                    "why_recommended": action.why_recommended or f"High-impact skill unlocking verified target opportunities in your career trajectory.",
                    "is_required": True,
                    "is_from_cosgo": True
                })

        # If COSGO provided recommendations, COSGO is the strict single source of truth.
        # Fall back to role matrix only if no COSGO recommendations exist.
        if not skill_gaps:
            norm_known_lower = {s.lower() for s in candidate_skills}
            primary_role = target_roles[0].lower() if target_roles else "backend"
            role_key = "backend"
            for k in ROLE_CORE_SKILLS:
                if k in primary_role:
                    role_key = k
                    break

            role_info = ROLE_CORE_SKILLS.get(role_key, ROLE_CORE_SKILLS["backend"])
            for req_skill in role_info["required"]:
                if req_skill.lower() not in norm_known_lower and req_skill.lower() not in addressed_skill_names:
                    addressed_skill_names.add(req_skill.lower())
                    est_hrs = role_info["hours"].get(req_skill, 15.0)
                    skill_gaps.append({
                        "skill_name": req_skill,
                        "category": "Core Requirement",
                        "estimated_hours": float(est_hrs),
                        "is_estimate": True,
                        "prerequisites": SKILL_PREREQUISITES.get(req_skill.lower(), []),
                        "priority_rank": len(skill_gaps) + 1,
                        "marginal_gain": 0.20,
                        "why_recommended": f"Fundamental required competency for {target_roles[0]} positions.",
                        "is_required": True,
                        "is_from_cosgo": False
                    })

            for opt_skill in role_info["optional"]:
                if opt_skill.lower() not in norm_known_lower and opt_skill.lower() not in addressed_skill_names:
                    addressed_skill_names.add(opt_skill.lower())
                    est_hrs = role_info["hours"].get(opt_skill, 12.0)
                    skill_gaps.append({
                        "skill_name": opt_skill,
                        "category": "High-Value Elective",
                        "estimated_hours": float(est_hrs),
                        "is_estimate": True,
                        "prerequisites": SKILL_PREREQUISITES.get(opt_skill.lower(), []),
                        "priority_rank": len(skill_gaps) + 1,
                        "marginal_gain": 0.10,
                        "why_recommended": f"Differentiating modern skill expanding your technical versatility.",
                        "is_required": False,
                        "is_from_cosgo": False
                    })

        # 4. Attach Verified Learning Resources to Each Skill
        enriched_skills: List[Dict[str, Any]] = []
        yt = YouTubeAdapter()

        for item in skill_gaps:
            s_name = item["skill_name"]
            status = "VERIFIED_KNOWN" if s_name.lower() in norm_known_lower else "CRITICAL_GAP"
            if s_name in (plan.completed_skills or []):
                status = "COMPLETED"

            # A. Documentation
            doc = DocCatalogService.resolve_documentation(s_name)

            # B. Courses
            courses = await CourseCatalogService.find_courses_for_skills([s_name], limit_per_skill=2)

            # C. Certifications
            certs = CertificationDirectoryService.find_certifications_for_skills_and_roles([s_name], target_roles, limit=2)

            # D. Videos
            videos = []
            if include_youtube:
                videos = await yt.search_videos(s_name, limit=2, prefer_curated_fallback=True)

            enriched_skills.append({
                **item,
                "status": status,
                "documentation": doc.model_dump() if doc else None,
                "courses": [c.model_dump() for c in courses],
                "certifications": [cert.model_dump() for cert in certs],
                "videos": videos
            })

        # 5. Construct Phased Learning Plan (respecting weekly hours budget)
        weekly_budget = plan.weekly_hours_budget
        total_hours = sum(s["estimated_hours"] for s in enriched_skills if s["status"] != "COMPLETED")
        estimated_weeks = math.ceil(total_hours / weekly_budget) if weekly_budget > 0 else 1

        # Partition into ordered phases (Prerequisites first, then core, then advanced)
        phases: List[Dict[str, Any]] = []
        current_phase_skills: List[Dict[str, Any]] = []
        accumulated_phase_hours = 0.0
        phase_num = 1

        for skill in enriched_skills:
            current_phase_skills.append(skill)
            accumulated_phase_hours += skill["estimated_hours"]

            # Break into phase roughly every 20-30 hours or 2-3 skills
            if accumulated_phase_hours >= 20.0 or len(current_phase_skills) >= 2:
                phase_weeks = math.ceil(accumulated_phase_hours / weekly_budget)
                phases.append({
                    "phase_number": phase_num,
                    "title": f"Phase {phase_num}: " + (
                        "Foundational Architecture" if phase_num == 1 else
                        ("Production Tooling & Systems" if phase_num == 2 else "Advanced Scalability & Electives")
                    ),
                    "skills": current_phase_skills,
                    "total_hours": round(accumulated_phase_hours, 1),
                    "estimated_weeks": phase_weeks
                })
                phase_num += 1
                current_phase_skills = []
                accumulated_phase_hours = 0.0

        if current_phase_skills:
            phase_weeks = math.ceil(accumulated_phase_hours / weekly_budget)
            phases.append({
                "phase_number": phase_num,
                "title": f"Phase {phase_num}: Advanced Cloud & Distributed Systems",
                "skills": current_phase_skills,
                "total_hours": round(accumulated_phase_hours, 1),
                "estimated_weeks": phase_weeks
            })

        # 6. Profile-Aware Project Recommendations
        recommended_projects = ProjectRecommenderService.recommend_projects(
            candidate_skills=list(candidate_skills),
            skill_gaps=[s["skill_name"] for s in enriched_skills],
            target_roles=target_roles,
            existing_projects=existing_projects,
            available_hours=total_hours,
            limit=3
        )

        # Attach official documentation to recommended projects
        for proj in recommended_projects:
            for s in proj.target_skills:
                d = DocCatalogService.resolve_documentation(s)
                if d and not any(l["url"] == d.url for l in proj.documentation_links):
                    proj.documentation_links.append({"title": d.title, "url": d.url})

        return {
            "is_onboarding_empty_state": False,
            "weekly_hours_budget": weekly_budget,
            "total_estimated_hours": round(total_hours, 1),
            "total_estimated_weeks": estimated_weeks,
            "target_roles": target_roles,
            "candidate_known_skills": sorted(list(candidate_skills)),
            "candidate_experience": candidate_experience,
            "recommended_skills": enriched_skills,
            "learning_phases": phases,
            "recommended_projects": [p.model_dump() for p in recommended_projects],
            "catalog_overview": {
                "total_documentation_pages": len(DocCatalogService.get_all_documentation()),
                "total_verified_courses": len(CourseCatalogService.get_all_courses()),
                "total_certifications": len(CertificationDirectoryService.get_all_certifications())
            }
        }

    @classmethod
    async def get_cosgo_learning_dashboard(
        cls,
        user_id: str,
        db: Session,
        requested_skill: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execution layer of COSGO:
        - COSGO is the single source of truth for recommended skills.
        - If no valid COSGO recommendations exist, returns is_cosgo_empty_state=True.
        - Provides a skill selector containing exclusively COSGO-recommended skills.
        - For the selected skill, constructs a strictly relevant learning plan:
            A. Skill Overview (why recommended, opportunities helped, coverage gain, effort, prerequisites)
            B. Structured 4-stage learning roadmap (Fundamentals, Intermediate, Practical, Advanced)
            C. Verified official documentation, relevant free courses, certifications, and video tutorials
            D. Strictly relevant practical project blueprints and exercises
            E. User-controlled honest progress tracking
        """
        # 1. Fetch latest persisted COSGO run
        latest_cosgo = (
            db.query(CosgoRun)
            .filter(CosgoRun.user_id == user_id)
            .order_by(desc(CosgoRun.created_at))
            .first()
        )

        plan = cls.get_or_create_user_plan(user_id, db)

        # 2. Check for empty state: No valid COSGO run or zero actions
        if not latest_cosgo or not latest_cosgo.actions:
            return {
                "is_cosgo_empty_state": True,
                "empty_state_message": "No active Skill Gap Optimization recommendations found. Run Cross-Opportunity Skill Gap Optimization (COSGO) in Skill Gap & Roadmap to identify the highest-impact skills for your target opportunities.",
                "run_id": None,
                "algorithm_version": None,
                "budget_hours": 0.0,
                "weekly_hours_budget": plan.weekly_hours_budget,
                "baseline_coverage": 0.0,
                "projected_coverage": 0.0,
                "marginal_coverage_increase": 0.0,
                "recommended_skills": [],
                "selected_skill_name": None,
                "skill_plan": None
            }

        # 3. Build COSGO-recommended skills selector list
        sorted_actions = sorted(latest_cosgo.actions, key=lambda a: a.priority_rank)
        recommended_skills = []
        for act in sorted_actions:
            p_state = act.progress_state.value if hasattr(act.progress_state, "value") else str(act.progress_state)
            recommended_skills.append({
                "action_id": act.id,
                "skill_name": act.skill_name,
                "priority_rank": act.priority_rank,
                "marginal_coverage_gain": act.marginal_coverage_gain,
                "cumulative_coverage": act.cumulative_coverage,
                "opportunities_count": act.opportunities_count,
                "estimated_hours": act.estimated_hours,
                "effort_uncertainty_range": act.effort_uncertainty_range or {},
                "prerequisites": act.prerequisites or [],
                "category": act.category,
                "progress_state": p_state,
                "why_recommended": act.why_recommended
            })

        # 4. Determine selected skill
        selected_action = None
        diagnostic_note = None
        if requested_skill and requested_skill.strip():
            clean_req = requested_skill.strip().lower()
            selected_action = next((a for a in sorted_actions if a.skill_name.lower() == clean_req), None)
            if not selected_action:
                diagnostic_note = f"Skill '{requested_skill}' is no longer in your active COSGO optimization. Displaying top-priority skill '{sorted_actions[0].skill_name}' instead."

        if not selected_action:
            selected_action = sorted_actions[0]

        # 5. Load Candidate Facts & Progress
        facts = cls.gather_candidate_facts(user_id, db)
        all_skill_progress = plan.project_progress.get("skill_progress", {}) if isinstance(plan.project_progress, dict) else {}
        skill_progress = all_skill_progress.get(selected_action.skill_name, {})

        completed_resources = set(skill_progress.get("completed_resources", []))
        completed_milestones = set(skill_progress.get("completed_milestones", []))
        completed_exercises = set(skill_progress.get("completed_exercises", []))
        project_milestones_completed = set(skill_progress.get("project_milestones_completed", []))
        project_completed = bool(skill_progress.get("project_completed", False))

        # 6. Structured 4-stage learning roadmap
        curriculum = SkillCurriculumService.get_skill_curriculum(
            skill_name=selected_action.skill_name,
            estimated_hours=selected_action.estimated_hours,
            prerequisites=selected_action.prerequisites,
            category=selected_action.category
        )

        roadmap_stages = []
        for stg in curriculum.stages:
            stg_dict = stg.model_dump()
            stg_dict["is_completed"] = stg.stage_id in completed_milestones
            roadmap_stages.append(stg_dict)

        exercises = []
        for ex in curriculum.practical_exercises:
            ex_dict = ex.model_dump()
            ex_dict["is_completed"] = ex.id in completed_exercises
            exercises.append(ex_dict)

        # 7. Strictly Relevant Learning Resources
        doc = DocCatalogService.resolve_documentation(selected_action.skill_name)
        doc_dict = None
        if doc:
            doc_dict = doc.model_dump()
            doc_dict["is_completed"] = doc.url in completed_resources

        courses = CourseCatalogService.get_courses_for_skill(selected_action.skill_name, limit=4)
        courses_list = []
        for c in courses:
            c_dict = c.model_dump()
            c_dict["is_completed"] = c.url in completed_resources
            courses_list.append(c_dict)

        certs = CertificationDirectoryService.get_certifications_for_skill(selected_action.skill_name, limit=4)
        certs_list = []
        for cert in certs:
            cert_dict = cert.model_dump()
            cert_dict["is_completed"] = cert.official_url in completed_resources
            certs_list.append(cert_dict)

        yt = YouTubeAdapter()
        videos = await yt.search_videos(selected_action.skill_name, limit=3, prefer_curated_fallback=True)

        # 8. Strictly Relevant Practical Projects
        projects = ProjectRecommenderService.get_projects_for_skill(
            selected_action.skill_name,
            existing_projects=facts["existing_projects"],
            limit=3
        )
        projects_list = []
        for p in projects:
            p_dict = p.model_dump()
            p_dict["is_completed"] = project_completed or p.project_id in completed_resources
            for m in p_dict["milestones"]:
                m["is_completed"] = m["step_number"] in project_milestones_completed
            projects_list.append(p_dict)

        act_progress = selected_action.progress_state.value if hasattr(selected_action.progress_state, "value") else str(selected_action.progress_state)

        skill_plan = {
            "skill_name": selected_action.skill_name,
            "action_id": selected_action.id,
            "run_id": latest_cosgo.id,
            "priority_rank": selected_action.priority_rank,
            "category": selected_action.category,
            "why_recommended": selected_action.why_recommended,
            "opportunities_count": selected_action.opportunities_count,
            "target_opportunities_summary": selected_action.target_opportunities_summary or [],
            "marginal_coverage_gain": selected_action.marginal_coverage_gain,
            "cumulative_coverage": selected_action.cumulative_coverage,
            "estimated_hours": selected_action.estimated_hours,
            "effort_uncertainty_range": selected_action.effort_uncertainty_range or {},
            "prerequisites": selected_action.prerequisites or [],
            "progress_state": act_progress,
            "completed_at": selected_action.completed_at.isoformat() if selected_action.completed_at else None,
            "diagnostic_note": diagnostic_note,
            "roadmap_stages": roadmap_stages,
            "resources": {
                "documentation": doc_dict,
                "courses": courses_list,
                "certifications": certs_list,
                "videos": videos,
                "practical_exercises": exercises
            },
            "projects": projects_list,
            "progress": {
                "completed_resources": list(completed_resources),
                "completed_milestones": list(completed_milestones),
                "completed_exercises": list(completed_exercises),
                "project_milestones_completed": list(project_milestones_completed),
                "project_completed": project_completed,
                "overall_status": act_progress
            }
        }

        return {
            "is_cosgo_empty_state": False,
            "empty_state_message": None,
            "run_id": latest_cosgo.id,
            "algorithm_version": latest_cosgo.algorithm_version,
            "budget_hours": latest_cosgo.budget_hours,
            "weekly_hours_budget": latest_cosgo.weekly_budget_hours or plan.weekly_hours_budget,
            "baseline_coverage": latest_cosgo.baseline_coverage,
            "projected_coverage": latest_cosgo.projected_coverage,
            "marginal_coverage_increase": latest_cosgo.marginal_coverage_increase,
            "recommended_skills": recommended_skills,
            "selected_skill_name": selected_action.skill_name,
            "skill_plan": skill_plan
        }

    @classmethod
    def update_learning_progress(
        cls,
        user_id: str,
        payload: Dict[str, Any],
        db: Session
    ) -> Dict[str, Any]:
        """
        Updates learning progress for a specific skill and synchronizes with CosgoAction.
        - Supports toggling resources, milestone stages, exercises, and project steps.
        - Supports updating overall progress state (RECOMMENDED, PLANNED, IN_PROGRESS, COMPLETED).
        - Strictly associates progress with the intended skill.
        """
        skill_name = payload.get("skill_name", "").strip()
        if not skill_name:
            raise ValueError("skill_name is required for progress tracking.")

        plan = cls.get_or_create_user_plan(user_id, db)
        if not isinstance(plan.project_progress, dict):
            plan.project_progress = {}

        skill_progress = plan.project_progress.setdefault("skill_progress", {})
        data = skill_progress.setdefault(skill_name, {
            "completed_resources": [],
            "completed_milestones": [],
            "completed_exercises": [],
            "project_milestones_completed": [],
            "project_completed": False
        })

        # 1. Toggle resource completion
        toggle_res = payload.get("toggle_resource_url")
        if toggle_res:
            res_list = data.setdefault("completed_resources", [])
            if toggle_res in res_list:
                res_list.remove(toggle_res)
            else:
                res_list.append(toggle_res)

        # 2. Toggle roadmap milestone completion
        toggle_m = payload.get("toggle_milestone_id")
        if toggle_m:
            m_list = data.setdefault("completed_milestones", [])
            if toggle_m in m_list:
                m_list.remove(toggle_m)
            else:
                m_list.append(toggle_m)

        # 3. Toggle practical exercise completion
        toggle_ex = payload.get("toggle_exercise_id")
        if toggle_ex:
            ex_list = data.setdefault("completed_exercises", [])
            if toggle_ex in ex_list:
                ex_list.remove(toggle_ex)
            else:
                ex_list.append(toggle_ex)

        # 4. Toggle project completion
        if payload.get("toggle_project_id"):
            data["project_completed"] = not data.get("project_completed", False)

        # 5. Toggle project milestone step
        toggle_step = payload.get("toggle_project_milestone_step")
        if toggle_step is not None:
            steps_list = data.setdefault("project_milestones_completed", [])
            if toggle_step in steps_list:
                steps_list.remove(toggle_step)
            else:
                steps_list.append(toggle_step)

        # 6. Overall progress state synchronization with CosgoAction
        new_state = payload.get("progress_state")
        updated_action_state = None
        if new_state:
            try:
                valid_enum = CosgoProgressState(new_state.upper())
                data["status"] = valid_enum.value
                
                # Also synchronize with latest CosgoAction
                latest_cosgo = (
                    db.query(CosgoRun)
                    .filter(CosgoRun.user_id == user_id)
                    .order_by(desc(CosgoRun.created_at))
                    .first()
                )
                if latest_cosgo:
                    action = next(
                        (a for a in latest_cosgo.actions if a.skill_name.lower() == skill_name.lower()),
                        None
                    )
                    if action:
                        action.progress_state = valid_enum
                        if valid_enum == CosgoProgressState.COMPLETED:
                            action.completed_at = datetime.now(timezone.utc)
                            if skill_name not in (plan.completed_skills or []):
                                plan.completed_skills = list(set((plan.completed_skills or []) + [skill_name]))
                        else:
                            action.completed_at = None
                            if plan.completed_skills and skill_name in plan.completed_skills:
                                plan.completed_skills = [s for s in plan.completed_skills if s != skill_name]
                        if payload.get("user_notes"):
                            action.user_notes = payload["user_notes"]
                        updated_action_state = valid_enum.value
            except ValueError:
                pass

        flag_modified(plan, "project_progress")
        flag_modified(plan, "completed_skills")
        plan.updated_at = datetime.now(timezone.utc)
        db.commit()

        return {
            "skill_name": skill_name,
            "progress": data,
            "progress_state": updated_action_state or data.get("status", "RECOMMENDED")
        }
