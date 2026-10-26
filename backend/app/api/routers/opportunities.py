from typing import List, Optional, Dict, Any
import asyncio
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, case

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.opportunity import Opportunity, OpportunityType, OpportunityStatus, RecommendedAction
from app.models.company import Company
from app.models.job import Job, JobRequirement
from app.models.profile import Profile, Skill
from app.models.discovery import AgentRun, RunStatus
from app.schemas.opportunity import (
    OpportunityRead, OpportunityStatusUpdate, DiscoveryRunRequest, DiscoveryRunRead,
    FilterSuggestionsRead
)
from app.schemas.company import CompanyRead
from app.services.opportunity_orchestrator import OpportunityOrchestrator
from app.services.profile_intelligence import ProfileIntelligenceService

router = APIRouter(prefix="/opportunities", tags=["Opportunities & Discovery"])


@router.post("/discovery", response_model=DiscoveryRunRead, status_code=status.HTTP_202_ACCEPTED)
def start_opportunity_discovery(
    request: DiscoveryRunRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Triggers an asynchronous multi-source Opportunity Intelligence discovery run.
    Queries Tavily, Exa, and configured specialized job APIs.
    """
    run = OpportunityOrchestrator.start_discovery_run(db, current_user, request)
    # Dispatch async background task
    background_tasks.add_task(
        OpportunityOrchestrator.execute_discovery_run_sync,
        run_id=run.id,
        user_id=current_user.id,
        request_params=request.model_dump()
    )
    return run


@router.post("/auto-discover", response_model=Optional[DiscoveryRunRead], status_code=status.HTTP_202_ACCEPTED)
def auto_discover_opportunities(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Profile-aware initial opportunity discovery.
    1. If user already has stored opportunities, returns None (no duplicate run needed).
    2. If a discovery run is already active or completed in the last 6 hours, returns that run.
    3. If no opportunities exist, checks user's profile completeness.
       If sufficiently complete, triggers an initial discovery run automatically.
       If incomplete, raises HTTP 400 detailing what is needed.
    """
    # Check if user already has persisted opportunities
    existing_opp_count = db.query(func.count(Opportunity.id)).filter(Opportunity.user_id == current_user.id).scalar() or 0
    if existing_opp_count > 0:
        return None

    # Check for recent or active runs
    recent_run = (
        db.query(AgentRun)
        .filter(AgentRun.user_id == current_user.id)
        .order_by(AgentRun.created_at.desc())
        .first()
    )
    if recent_run:
        # If currently running or queued, don't start duplicate
        if recent_run.status in (RunStatus.RUNNING, RunStatus.QUEUED):
            return recent_run
        # If completed within last 6 hours, return it
        if recent_run.created_at and (datetime.now(timezone.utc) - recent_run.created_at.replace(tzinfo=timezone.utc if recent_run.created_at.tzinfo is None else recent_run.created_at.tzinfo)) < timedelta(hours=6):
            return recent_run

    # Check profile intelligence completeness
    candidate_intel = ProfileIntelligenceService.generate_candidate_intelligence(db, current_user)
    target_roles = [d.target_role for d in candidate_intel.career_directions]
    if not target_roles and candidate_intel.preferences.get("desired_roles"):
        target_roles = candidate_intel.preferences["desired_roles"]

    if not target_roles:
        missing_fields = []
        if not candidate_intel.career_directions:
            missing_fields.append("desired role or target career direction")
        if not candidate_intel.verified_skills:
            missing_fields.append("verified technical skills (upload resume)")
        
        detail_msg = (
            f"Your profile requires additional information before auto-discovery can recommend opportunities. "
            f"Please update: {', '.join(missing_fields)} at /profile or upload a resume at /resumes."
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail_msg
        )

    # Initiate profile-aware discovery
    req = DiscoveryRunRequest(
        target_roles=target_roles[:2],
        skills=[s.name for s in candidate_intel.verified_skills][:5],
        locations=candidate_intel.preferences.get("preferred_locations") or ["India", "Remote"],
        remote_preference=candidate_intel.preferences.get("remote_preference") or "flexible",
        limit=20
    )

    run = OpportunityOrchestrator.start_discovery_run(db, current_user, req)
    background_tasks.add_task(
        OpportunityOrchestrator.execute_discovery_run_sync,
        run_id=run.id,
        user_id=current_user.id,
        request_params=req.model_dump()
    )
    return run


@router.get("/discovery/{run_id}", response_model=DiscoveryRunRead)
def get_discovery_run_status(
    run_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns the real-time execution status and audit trail of a discovery run.
    """
    run = db.query(AgentRun).filter(AgentRun.id == run_id, AgentRun.user_id == current_user.id).first()
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Discovery run not found.")
    return run


@router.get("/runs", response_model=List[DiscoveryRunRead])
def list_discovery_runs(
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns the history of agent runs and discovery audit trails for the current user.
    """
    runs = (
        db.query(AgentRun)
        .filter(AgentRun.user_id == current_user.id)
        .order_by(AgentRun.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return runs


@router.get("/filter-suggestions", response_model=FilterSuggestionsRead)
def get_filter_suggestions(
    q: Optional[str] = Query(None, description="Optional search filter for suggestions"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns distinct canonical locations and skills from discovered opportunities
    and candidate profiles for autocomplete suggestions.
    """
    CANONICAL_CITY_MAP = {
        "bengaluru": "Bengaluru",
        "bangalore": "Bengaluru",
        "mohali": "Mohali",
        "noida": "Noida",
        "greater noida": "Greater Noida",
        "gurugram": "Gurugram",
        "gurgaon": "Gurugram",
        "hyderabad": "Hyderabad",
        "pune": "Pune",
        "mumbai": "Mumbai",
        "chennai": "Chennai",
        "delhi": "Delhi",
        "new delhi": "New Delhi",
        "remote": "Remote",
        "san francisco": "San Francisco",
        "new york": "New York",
        "seattle": "Seattle",
        "london": "London",
        "india": "India"
    }

    # Query distinct locations from Job linked to user's opportunities
    raw_job_locs = (
        db.query(Job.location)
        .join(Opportunity, Opportunity.job_id == Job.id)
        .filter(Opportunity.user_id == current_user.id, Job.location.isnot(None))
        .distinct()
        .all()
    )
    raw_comp_locs = (
        db.query(Company.headquarters)
        .join(Opportunity, Opportunity.company_id == Company.id)
        .filter(Opportunity.user_id == current_user.id, Company.headquarters.isnot(None))
        .distinct()
        .all()
    )

    all_raw_locations = [r[0] for r in raw_job_locs if r[0]] + [r[0] for r in raw_comp_locs if r[0]]
    
    canonical_locs = set()
    for raw in all_raw_locations:
        raw_clean = raw.strip()
        lower_raw = raw_clean.lower()
        matched = False
        for key, canonical in CANONICAL_CITY_MAP.items():
            if key in lower_raw:
                canonical_locs.add(canonical)
                matched = True
        if not matched and len(raw_clean) > 2:
            primary = raw_clean.split(",")[0].strip().title()
            canonical_locs.add(primary)

    # Always ensure popular canonical hubs are present
    for default_loc in ["Bengaluru", "Mohali", "Noida", "Gurugram", "Hyderabad", "Pune", "Mumbai", "Remote"]:
        canonical_locs.add(default_loc)

    # Query job requirements of type 'skill' from user's opportunities
    raw_req_skills = (
        db.query(JobRequirement.description)
        .join(Job, JobRequirement.job_id == Job.id)
        .join(Opportunity, Opportunity.job_id == Job.id)
        .filter(Opportunity.user_id == current_user.id, JobRequirement.requirement_type == "skill")
        .distinct()
        .all()
    )
    raw_cand_skills = (
        db.query(Skill.name)
        .join(Profile, Skill.profile_id == Profile.id)
        .filter(Profile.user_id == current_user.id)
        .distinct()
        .all()
    )

    all_raw_skills = [r[0] for r in raw_req_skills if r[0]] + [r[0] for r in raw_cand_skills if r[0]]
    
    default_skills = [
        "Python", "FastAPI", "Docker", "React", "TypeScript", "JavaScript", 
        "PostgreSQL", "PyTorch", "Kubernetes", "AWS", "Go", "SQL", 
        "Machine Learning", "Node.js", "Redis", "Git", "REST APIs", "GraphQL"
    ]
    all_raw_skills.extend(default_skills)

    canonical_skills = set()
    for s in all_raw_skills:
        clean = s.strip()
        if len(clean) >= 2:
            canonical_skills.add(clean)

    sorted_locs = sorted(list(canonical_locs))
    sorted_skills = sorted(list(canonical_skills), key=lambda x: x.lower())

    if q:
        query_str = q.strip().lower()
        sorted_locs = [l for l in sorted_locs if query_str in l.lower()]
        sorted_skills = [s for s in sorted_skills if query_str in s.lower()]

    return FilterSuggestionsRead(
        locations=sorted_locs[:30],
        skills=sorted_skills[:50]
    )


@router.get("", response_model=List[OpportunityRead])
def list_opportunities(
    opportunity_type: Optional[OpportunityType] = Query(None, description="Filter by ADVERTISED, EMERGING, or STRATEGIC"),
    status: Optional[OpportunityStatus] = Query(None, description="Filter by ACTIVE, SAVED, or DISMISSED"),
    recommended_action: Optional[RecommendedAction] = Query(None, description="Filter by CONTACT_NOW, IMPROVE_FIRST, or SKIP"),
    search: Optional[str] = Query(None, description="Search by title or company name"),
    location: Optional[str] = Query(None, description="Filter by location or city"),
    work_arrangement: Optional[str] = Query(None, description="Filter by remote, hybrid, or onsite"),
    employment_type: Optional[str] = Query(None, description="Filter by full-time, internship, contract"),
    company_classification: Optional[str] = Query(None, description="Filter by startup, smb, mid_sized, enterprise"),
    min_score: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum match score threshold"),
    run_id: Optional[str] = Query(None, description="Filter opportunities discovered in specific run"),
    sort_by: Optional[str] = Query("match_score", description="Sort by 'match_score' or 'recent'"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Lists persisted opportunities discovered for the candidate with comprehensive combinable filters.
    """
    query = (
        db.query(Opportunity)
        .options(
            joinedload(Opportunity.job),
            joinedload(Opportunity.company),
            joinedload(Opportunity.evidence_items)
        )
        .filter(Opportunity.user_id == current_user.id)
    )

    if opportunity_type:
        query = query.filter(Opportunity.opportunity_type == opportunity_type)
    if status:
        query = query.filter(Opportunity.status == status)
    if recommended_action:
        query = query.filter(Opportunity.recommended_action == recommended_action)
    if min_score is not None:
        query = query.filter(Opportunity.match_score >= min_score)
    if run_id:
        query = query.filter(Opportunity.discovery_run_id == run_id)

    if search:
        search_filter = f"%{search.strip()}%"
        query = query.outerjoin(Opportunity.company).outerjoin(Opportunity.job).filter(
            (Company.name.ilike(search_filter)) | 
            (Job.title.ilike(search_filter)) | 
            (Opportunity.explanation.ilike(search_filter))
        )

    if location:
        clean_loc = location.strip()
        loc_filter = f"%{clean_loc}%"
        # Canonical location rule:
        # When an opportunity has a job, location is determined strictly by Job.location.
        # Only strategic / company-only opportunities without a job use Company.headquarters.
        loc_cond = case(
            (Opportunity.job_id.isnot(None), Job.location.ilike(loc_filter)),
            else_=Company.headquarters.ilike(loc_filter)
        )
        # Disambiguate "Noida" vs "Greater Noida"
        if clean_loc.lower() == "noida":
            loc_cond = loc_cond & ~case(
                (Opportunity.job_id.isnot(None), Job.location.ilike("%greater noida%")),
                else_=Company.headquarters.ilike("%greater noida%")
            )
        # Disambiguate "Delhi" vs "New Delhi"
        elif clean_loc.lower() == "delhi":
            loc_cond = loc_cond & ~case(
                (Opportunity.job_id.isnot(None), Job.location.ilike("%new delhi%")),
                else_=Company.headquarters.ilike("%new delhi%")
            )

        query = query.outerjoin(Opportunity.job).outerjoin(Opportunity.company).filter(loc_cond)

    if work_arrangement:
        query = query.outerjoin(Opportunity.job).filter(
            Job.work_arrangement.ilike(f"%{work_arrangement.strip()}%")
        )

    if employment_type:
        query = query.outerjoin(Opportunity.job).filter(
            Job.employment_type.ilike(f"%{employment_type.strip()}%")
        )

    if company_classification:
        clean_cls = company_classification.lower().strip()
        if clean_cls in ("unknown", "unspecified"):
            query = query.outerjoin(Opportunity.company).filter(
                (Company.classification == "unknown") |
                (Company.classification == "unspecified") |
                (Company.classification.is_(None))
            )
        else:
            query = query.outerjoin(Opportunity.company).filter(
                Company.classification == clean_cls
            )

    # Order by selection
    if sort_by == "recent":
        opportunities = query.order_by(Opportunity.updated_at.desc(), Opportunity.match_score.desc()).offset(offset).limit(limit).all()
    else:
        opportunities = query.order_by(Opportunity.match_score.desc(), Opportunity.updated_at.desc()).offset(offset).limit(limit).all()

    return opportunities


# Company Endpoints (must precede /{opportunity_id} to prevent path shadowing)
@router.get("/companies/all", response_model=List[CompanyRead])
def list_companies(
    has_openings: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Lists discovered companies and their public research signals.
    """
    query = (
        db.query(Company)
        .join(Opportunity, Opportunity.company_id == Company.id)
        .filter(Opportunity.user_id == current_user.id)
        .distinct()
    )
    if has_openings is not None:
        query = query.filter(Company.has_advertised_openings == has_openings)

    return query.order_by(Company.alignment_score.desc()).offset(offset).limit(limit).all()


@router.get("/companies/{company_id}", response_model=CompanyRead)
def get_company(
    company_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieves detailed company profile, public expansion signals, and grounded contacts.
    """
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found.")
    return company


@router.get("/{opportunity_id}", response_model=OpportunityRead)
def get_opportunity(
    opportunity_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieves full details of an opportunity, including job requirements, company signals, and evidence citations.
    """
    opp = (
        db.query(Opportunity)
        .options(
            joinedload(Opportunity.job),
            joinedload(Opportunity.company),
            joinedload(Opportunity.evidence_items)
        )
        .filter(Opportunity.id == opportunity_id, Opportunity.user_id == current_user.id)
        .first()
    )
    if not opp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Opportunity not found.")
    return opp


@router.patch("/{opportunity_id}", response_model=OpportunityRead)
def update_opportunity_status(
    opportunity_id: str,
    payload: OpportunityStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Updates the status of an opportunity (e.g. SAVED, DISMISSED, ACTIVE).
    """
    opp = (
        db.query(Opportunity)
        .filter(Opportunity.id == opportunity_id, Opportunity.user_id == current_user.id)
        .first()
    )
    if not opp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Opportunity not found.")

    opp.status = payload.status
    db.commit()
    db.refresh(opp)
    return opp
