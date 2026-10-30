from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.services.learning.learning_plan_service import LearningPlanService
from app.services.learning.doc_catalog import DocCatalogService
from app.services.learning.course_catalog import CourseCatalogService
from app.services.learning.certification_directory import CertificationDirectoryService
from app.services.learning.project_recommender import ProjectRecommenderService
from app.services.providers.youtube_adapter import YouTubeAdapter

router = APIRouter(prefix="/learning", tags=["Learning Resources & Project Recommendations"])


class BudgetUpdateRequest(BaseModel):
    weekly_hours: float = Field(ge=2.0, le=60.0, description="Available study hours per week (2 - 60 hrs)")


class LearningProgressPayload(BaseModel):
    skill_name: str
    progress_state: Optional[str] = None
    toggle_resource_url: Optional[str] = None
    toggle_milestone_id: Optional[str] = None
    toggle_exercise_id: Optional[str] = None
    toggle_project_id: Optional[str] = None
    toggle_project_milestone_step: Optional[int] = None
    user_notes: Optional[str] = None


@router.get("/cosgo-plan")
async def get_cosgo_learning_plan(
    skill: Optional[str] = Query(default=None, description="Specific COSGO-recommended skill to inspect"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Execution Layer of COSGO:
    Returns the user's active COSGO recommendations queue and the full, strictly
    relevant learning plan for the selected skill (overview, 4-stage roadmap,
    verified documentation, courses, certs, projects, and honest progress).
    """
    return await LearningPlanService.get_cosgo_learning_dashboard(
        user_id=current_user.id,
        db=db,
        requested_skill=skill
    )


@router.patch("/progress")
def update_skill_learning_progress(
    payload: LearningProgressPayload,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Honest progress tracking for a specific skill:
    Toggles completion for resources, roadmap milestone stages, practical exercises,
    and portfolio project steps, and updates overall CosgoAction progress state.
    """
    try:
        return LearningPlanService.update_learning_progress(
            user_id=current_user.id,
            payload=payload.model_dump(),
            db=db
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/overview")
async def get_learning_overview(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns the candidate's personalized learning overview, skills gap roadmap,
    and tailored project blueprints based on profile, target roles, and COSGO optimization.
    """
    return await LearningPlanService.build_personalized_learning_overview(
        user_id=current_user.id,
        db=db,
        include_youtube=True
    )


@router.put("/budget")
def update_study_budget(
    payload: BudgetUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Updates the candidate's weekly study budget and saves preference.
    """
    plan = LearningPlanService.update_weekly_budget(
        user_id=current_user.id,
        weekly_hours=payload.weekly_hours,
        db=db
    )
    return {
        "user_id": current_user.id,
        "weekly_hours_budget": plan.weekly_hours_budget,
        "updated_at": plan.updated_at.isoformat() if plan.updated_at else None
    }


@router.get("/docs")
def search_documentation(
    query: Optional[str] = Query(default=None, description="Search term for technical documentation"),
    limit: int = Query(default=15, ge=1, le=50)
):
    """
    Returns verified official documentation from the curated technical catalog.
    Requires zero external API keys.
    """
    if query:
        docs = DocCatalogService.search_documentation(query, limit=limit)
    else:
        docs = DocCatalogService.get_all_documentation()[:limit]

    return [d.model_dump() for d in docs]


@router.get("/videos")
async def search_educational_videos(
    skill: str = Query(description="Technical skill or topic for video search"),
    limit: int = Query(default=3, ge=1, le=10)
):
    """
    Searches YouTube educational programming videos using official YouTube Data API.
    Gracefully falls back to curated verified tutorials if API key is not configured.
    """
    yt = YouTubeAdapter()
    videos = await yt.search_videos(query=skill, limit=limit, prefer_curated_fallback=True)
    return {
        "skill": skill,
        "provider": yt.provider_name,
        "is_live_api": yt.is_configured(),
        "circuit_status": yt.circuit_status,
        "results_count": len(videos),
        "videos": videos
    }


@router.get("/courses")
async def search_courses(
    skill: Optional[str] = Query(default=None, description="Skill filter for courses"),
    access_type: Optional[str] = Query(default=None, description="Access filter: FREE_COURSE or FREE_TO_AUDIT"),
    difficulty: Optional[str] = Query(default=None, description="Difficulty level filter")
):
    """
    Discovers verified free-to-audit and zero-cost courses from reputable institutions.
    """
    if skill:
        courses = await CourseCatalogService.find_courses_for_skills(
            skills=[skill],
            access_type_filter=access_type,
            difficulty_filter=difficulty
        )
    else:
        courses = CourseCatalogService.get_all_courses()
        if access_type:
            courses = [c for c in courses if c.access_type.name == access_type or c.access_type.value == access_type]
        if difficulty:
            courses = [c for c in courses if c.difficulty_level.lower() == difficulty.lower()]

    return [c.model_dump() for c in courses]


@router.get("/certifications")
def get_certifications(
    skill: Optional[str] = Query(default=None, description="Skill filter"),
    role: Optional[str] = Query(default=None, description="Target role filter")
):
    """
    Browse the official vendor certification directory with verified pricing transparency.
    """
    skills = [skill] if skill else []
    roles = [role] if role else []

    if skills or roles:
        certs = CertificationDirectoryService.find_certifications_for_skills_and_roles(
            skills=skills,
            roles=roles
        )
    else:
        certs = CertificationDirectoryService.get_all_certifications()

    return [cert.model_dump() for cert in certs]


@router.get("/projects")
def get_recommended_projects(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns profile-aware project blueprints designed to demonstrate competencies in high-priority skill gaps.
    """
    facts = LearningPlanService.gather_candidate_facts(current_user.id, db)
    target_roles = facts["target_roles"] or ["Software Engineer", "Backend Developer"]

    blueprints = ProjectRecommenderService.recommend_projects(
        candidate_skills=list(facts["candidate_skills"]),
        skill_gaps=[],
        target_roles=target_roles,
        existing_projects=facts["existing_projects"],
        limit=5
    )
    return [b.model_dump() for b in blueprints]


@router.get("/health")
def get_learning_provider_health():
    """
    Reports provider health, daily request limits, and catalog size metrics.
    Never exposes API keys or credential secrets.
    """
    yt = YouTubeAdapter()
    return {
        "youtube": yt.get_health_status(),
        "documentation_catalog": {
            "total_technologies": len(DocCatalogService.get_all_documentation()),
            "status": "active_curated"
        },
        "course_catalog": {
            "total_courses": len(CourseCatalogService.get_all_courses()),
            "status": "active_curated"
        },
        "certification_directory": {
            "total_certifications": len(CertificationDirectoryService.get_all_certifications()),
            "status": "active_curated"
        }
    }
