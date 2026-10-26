from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.cosgo import CosgoRun, CosgoAction
from app.schemas.cosgo import (
    CosgoOptimizeRequest,
    CosgoActionUpdateProgressRequest,
    CosgoBudgetUpdateRequest,
    CosgoActionResponse,
    CosgoRunResponse,
    CosgoCoverageMatrixResponse,
    CosgoBenchmarkResponse
)
from app.services.cosgo_service import CosgoService

router = APIRouter(prefix="/cosgo", tags=["COSGO: Skill Gap & Roadmap Optimization"])


@router.post("/optimize", response_model=CosgoRunResponse, status_code=status.HTTP_201_CREATED)
def run_optimization(
    payload: Optional[CosgoOptimizeRequest] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Triggers a fresh COSGO cross-opportunity skill gap optimization.
    Computes marginal coverage gain against the user's eligible target opportunities.
    """
    budget_hours = payload.budget_hours if payload and payload.budget_hours else 40.0
    weekly_budget_hours = payload.weekly_budget_hours if payload and payload.weekly_budget_hours else 10.0
    target_roles = payload.target_roles if payload else None
    min_rel = payload.min_opportunity_relevance if payload and payload.min_opportunity_relevance else 0.35

    run = CosgoService.run_optimization(
        user_id=current_user.id,
        db=db,
        budget_hours=budget_hours,
        weekly_budget_hours=weekly_budget_hours,
        target_roles=target_roles,
        min_relevance=min_rel
    )
    return _format_run_response(run)


@router.get("/latest", response_model=CosgoRunResponse)
def get_latest_recommendations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieves the user's latest persisted COSGO run.
    If no run exists yet, automatically generates an initial optimization.
    """
    run = CosgoService.get_or_create_latest_run(
        user_id=current_user.id,
        db=db
    )
    return _format_run_response(run)


@router.get("/runs", response_model=List[CosgoRunResponse])
def get_run_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(default=10, ge=1, le=50)
):
    """
    Retrieves the historical audit trail of COSGO runs for the authenticated user.
    """
    runs = db.query(CosgoRun).filter(
        CosgoRun.user_id == current_user.id
    ).order_by(desc(CosgoRun.created_at)).limit(limit).all()

    return [_format_run_response(r) for r in runs]


@router.get("/actions/{action_id}", response_model=CosgoActionResponse)
def get_action_details(
    action_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Inspects full coverage details and affected target opportunities for a specific action.
    """
    action = db.query(CosgoAction).filter(
        CosgoAction.id == action_id,
        CosgoAction.user_id == current_user.id
    ).first()

    if not action:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Action '{action_id}' not found."
        )

    return _format_action_response(action)


@router.patch("/actions/{action_id}/progress", response_model=CosgoActionResponse)
def update_action_progress(
    action_id: str,
    payload: CosgoActionUpdateProgressRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Updates the user's progress state (RECOMMENDED, PLANNED, IN_PROGRESS, COMPLETED).
    Does NOT automatically alter the candidate's verified profile without separate confirmation.
    """
    try:
        updated = CosgoService.update_action_progress(
            action_id=action_id,
            user_id=current_user.id,
            progress_state=payload.progress_state,
            user_notes=payload.user_notes,
            db=db
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Action '{action_id}' not found."
        )

    return _format_action_response(updated)


@router.put("/budget", response_model=CosgoRunResponse)
def update_budget_and_reoptimize(
    payload: CosgoBudgetUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Updates the candidate's learning-time budget and re-runs optimization.
    """
    weekly = payload.weekly_budget_hours or 10.0
    run = CosgoService.run_optimization(
        user_id=current_user.id,
        db=db,
        budget_hours=payload.budget_hours,
        weekly_budget_hours=weekly
    )
    return _format_run_response(run)


@router.get("/coverage-matrix", response_model=CosgoCoverageMatrixResponse)
def get_coverage_matrix(
    run_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieves the structured gap matrix across eligible opportunities and candidate skills.
    """
    if not run_id:
        latest = CosgoService.get_or_create_latest_run(current_user.id, db)
        run_id = latest.id

    matrix_res = CosgoService.get_coverage_matrix(run_id=run_id, user_id=current_user.id, db=db)
    if "error" in matrix_res:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=matrix_res["error"])

    return matrix_res


@router.get("/benchmark", response_model=CosgoBenchmarkResponse)
def get_benchmark_comparison(
    budget_hours: float = Query(default=35.0, ge=10.0, le=200.0),
    weekly_budget_hours: float = Query(default=10.0, ge=2.0, le=40.0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Phase K Research Reproducibility Endpoint:
    Compares COSGO against Frequency-Ranked, Independent Per-Job, and No-Effort Baselines.
    """
    eval_res = CosgoService.evaluate_benchmarks(
        user_id=current_user.id,
        db=db,
        budget_hours=budget_hours,
        weekly_budget_hours=weekly_budget_hours
    )
    if "error" in eval_res:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=eval_res["error"])

    return eval_res


# Response formatters
def _format_action_response(act: CosgoAction) -> Dict[str, Any]:
    return {
        "id": act.id,
        "run_id": act.run_id,
        "user_id": act.user_id,
        "skill_name": act.skill_name,
        "category": act.category,
        "priority_rank": act.priority_rank,
        "estimated_hours": act.estimated_hours,
        "effort_uncertainty_range": act.effort_uncertainty_range or {},
        "marginal_coverage_gain": act.marginal_coverage_gain,
        "cumulative_coverage": act.cumulative_coverage,
        "opportunities_count": act.opportunities_count,
        "target_opportunity_ids": act.target_opportunity_ids or [],
        "target_opportunities_summary": act.target_opportunities_summary or [],
        "prerequisites": act.prerequisites or [],
        "why_recommended": act.why_recommended,
        "practical_project": act.practical_project or {},
        "learning_resources": act.learning_resources or [],
        "progress_state": act.progress_state.value if hasattr(act.progress_state, 'value') else str(act.progress_state),
        "user_notes": act.user_notes,
        "completed_at": act.completed_at.isoformat() if act.completed_at else None,
        "created_at": act.created_at.isoformat() if act.created_at else ""
    }


def _format_run_response(run: CosgoRun) -> Dict[str, Any]:
    return {
        "id": run.id,
        "user_id": run.user_id,
        "budget_hours": run.budget_hours,
        "weekly_budget_hours": run.weekly_budget_hours,
        "target_roles": run.target_roles or [],
        "algorithm_version": run.algorithm_version,
        "status": run.status,
        "total_opportunities_analyzed": run.total_opportunities_analyzed,
        "eligible_opportunities_count": run.eligible_opportunities_count,
        "excluded_opportunities_count": run.excluded_opportunities_count,
        "baseline_coverage": run.baseline_coverage,
        "projected_coverage": run.projected_coverage,
        "marginal_coverage_increase": run.marginal_coverage_increase,
        "opportunities_at_threshold_baseline": run.opportunities_at_threshold_baseline,
        "opportunities_at_threshold_projected": run.opportunities_at_threshold_projected,
        "diagnostics": run.diagnostics or {},
        "actions": [_format_action_response(a) for a in run.actions],
        "created_at": run.created_at.isoformat() if run.created_at else "",
        "updated_at": run.updated_at.isoformat() if run.updated_at else ""
    }
