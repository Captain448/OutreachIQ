import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.db.session import get_db
from app.models.user import User
from app.models.opportunity import Opportunity
from app.models.resume import Resume
from app.models.job import Job
from app.models.company import Company
from app.models.outreach import OutreachDraft, OutreachPurpose, RecipientType, GenerationStatus
from app.schemas.outreach import (
    OutreachDraftCreate,
    OutreachDraftUpdate,
    OutreachGenerateRequest,
    OutreachDraftResponse,
    OutreachDraftListResponse,
    EligibleOpportunitySummary
)
from app.services.outreach_context_builder import OutreachContextBuilder
from app.services.outreach_service import OutreachService
from app.api.deps import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/outreach", tags=["Outreach"])


def _format_draft_response(draft: OutreachDraft) -> OutreachDraftResponse:
    """Helper to enrich OutreachDraftResponse with associated Job/Company metadata."""
    job_title = None
    company_name = None
    job_location = None
    application_url = None
    is_verified_opening = None
    verification_status = None

    if draft.opportunity and draft.opportunity.job:
        job = draft.opportunity.job
        job_title = job.title
        company_name = job.company_name
        job_location = job.location
        application_url = job.application_url or job.primary_url
        is_verified_opening = job.is_verified
        verification_status = job.verification_status
    elif draft.context_snapshot and "job" in draft.context_snapshot:
        j_ctx = draft.context_snapshot["job"]
        job_title = j_ctx.get("title")
        company_name = j_ctx.get("company_name")
        job_location = j_ctx.get("location")
        application_url = j_ctx.get("application_url") or j_ctx.get("primary_url")
        is_verified_opening = j_ctx.get("is_verified_opening")
        verification_status = j_ctx.get("verification_status")

    return OutreachDraftResponse(
        id=draft.id,
        user_id=draft.user_id,
        opportunity_id=draft.opportunity_id,
        resume_id=draft.resume_id,
        purpose=draft.purpose,
        recipient_type=draft.recipient_type,
        recipient_name=draft.recipient_name,
        recipient_role=draft.recipient_role,
        subject=draft.subject,
        body=draft.body,
        generation_status=draft.generation_status,
        model_provider=draft.model_provider,
        model_name=draft.model_name,
        context_snapshot=draft.context_snapshot or {},
        is_user_edited=draft.is_user_edited,
        user_notes=draft.user_notes,
        created_at=draft.created_at,
        updated_at=draft.updated_at,
        job_title=job_title,
        company_name=company_name,
        job_location=job_location,
        application_url=application_url,
        is_verified_opening=is_verified_opening,
        verification_status=verification_status
    )


@router.get("/opportunities", response_model=List[EligibleOpportunitySummary])
def get_eligible_opportunities(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieves candidate's persisted opportunities suitable for outreach,
    including title, company, location, match score, and verification status.
    """
    opps = (
        db.query(Opportunity)
        .filter(Opportunity.user_id == current_user.id)
        .order_by(Opportunity.match_score.desc(), Opportunity.created_at.desc())
        .all()
    )

    results = []
    for opp in opps:
        job = opp.job
        company = opp.company
        title = job.title if job else "Software Engineer"
        comp_name = job.company_name if job else (company.name if company else "Company")
        loc = job.location if job else None
        app_url = job.application_url or job.primary_url if job else None
        is_ver = job.is_verified if job else False
        ver_stat = job.verification_status if job else "LISTING_FOUND_STATUS_UNVERIFIED"

        results.append(EligibleOpportunitySummary(
            id=opp.id,
            job_title=title,
            company_name=comp_name,
            location=loc,
            match_score=opp.match_score,
            application_url=app_url,
            is_verified=is_ver,
            verification_status=ver_stat,
            matched_skills=opp.matched_skills or [],
            missing_skills=opp.missing_skills or [],
            created_at=opp.created_at
        ))

    return results


@router.get("/drafts", response_model=OutreachDraftListResponse)
def list_outreach_drafts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Lists all saved outreach drafts for the authenticated candidate,
    strictly isolated to the authenticated user.
    """
    drafts = (
        db.query(OutreachDraft)
        .filter(OutreachDraft.user_id == current_user.id)
        .order_by(OutreachDraft.updated_at.desc())
        .all()
    )

    items = [_format_draft_response(d) for d in drafts]
    return OutreachDraftListResponse(items=items, total=len(items))


@router.post("/drafts", response_model=OutreachDraftResponse, status_code=status.HTTP_201_CREATED)
def create_outreach_draft(
    payload: OutreachDraftCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Creates an outreach draft for a selected opportunity.
    Performs server-side authorization check ensuring opportunity and resume belong to user.
    Optionally invokes AI generation immediately or creates a structured manual starter draft.
    """
    # Authorization check: opportunity ownership
    opportunity = (
        db.query(Opportunity)
        .filter(Opportunity.id == payload.opportunity_id, Opportunity.user_id == current_user.id)
        .first()
    )
    if not opportunity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Opportunity not found or does not belong to the authenticated user."
        )

    # Authorization check: resume ownership (if provided)
    if payload.resume_id:
        resume = (
            db.query(Resume)
            .filter(Resume.id == payload.resume_id, Resume.user_id == current_user.id)
            .first()
        )
        if not resume:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Selected resume not found or does not belong to the authenticated user."
            )

    # Build grounded context
    try:
        context = OutreachContextBuilder.build_context(
            db=db,
            user_id=current_user.id,
            opportunity_id=payload.opportunity_id,
            resume_id=payload.resume_id,
            recipient_name=payload.recipient_name,
            recipient_role=payload.recipient_role,
            purpose=payload.purpose.value,
            recipient_type=payload.recipient_type.value
        )
    except Exception as e:
        logger.error(f"Failed to build outreach context: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # Generate draft content
    if payload.generate_immediately:
        try:
            draft_content = OutreachService.generate_draft_content(context)
        except Exception as e:
            logger.warning(f"AI generation failed: {str(e)}. Falling back to manual starter draft.")
            draft_content = OutreachService.create_manual_starter_draft(context)
            draft_content["status"] = GenerationStatus.FAILED
    else:
        draft_content = OutreachService.create_manual_starter_draft(context)

    # Save to database
    new_draft = OutreachDraft(
        user_id=current_user.id,
        opportunity_id=payload.opportunity_id,
        resume_id=payload.resume_id,
        purpose=payload.purpose,
        recipient_type=payload.recipient_type,
        recipient_name=payload.recipient_name,
        recipient_role=payload.recipient_role,
        subject=draft_content.get("subject", ""),
        body=draft_content.get("body", ""),
        generation_status=draft_content.get("status", GenerationStatus.DRAFT),
        model_provider=draft_content.get("model_provider"),
        model_name=draft_content.get("model_name"),
        context_snapshot=context,
        is_user_edited=False
    )
    db.add(new_draft)
    db.commit()
    db.refresh(new_draft)

    return _format_draft_response(new_draft)


@router.get("/drafts/{draft_id}", response_model=OutreachDraftResponse)
def get_outreach_draft(
    draft_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieves a single outreach draft by ID.
    Enforces strict user isolation: returns 404 if draft does not belong to user.
    """
    draft = (
        db.query(OutreachDraft)
        .filter(OutreachDraft.id == draft_id, OutreachDraft.user_id == current_user.id)
        .first()
    )
    if not draft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Outreach draft not found or access denied."
        )

    return _format_draft_response(draft)


@router.put("/drafts/{draft_id}", response_model=OutreachDraftResponse)
def update_outreach_draft(
    draft_id: str,
    payload: OutreachDraftUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Updates an outreach draft's subject, body, notes, or metadata.
    Marks is_user_edited=True and generation_status=MANUALLY_EDITED.
    """
    draft = (
        db.query(OutreachDraft)
        .filter(OutreachDraft.id == draft_id, OutreachDraft.user_id == current_user.id)
        .first()
    )
    if not draft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Outreach draft not found or access denied."
        )

    if payload.subject is not None:
        draft.subject = payload.subject
        draft.is_user_edited = True
    if payload.body is not None:
        draft.body = payload.body
        draft.is_user_edited = True
    if payload.purpose is not None:
        draft.purpose = payload.purpose
    if payload.recipient_type is not None:
        draft.recipient_type = payload.recipient_type
    if payload.recipient_name is not None:
        draft.recipient_name = payload.recipient_name
    if payload.recipient_role is not None:
        draft.recipient_role = payload.recipient_role
    if payload.user_notes is not None:
        draft.user_notes = payload.user_notes

    if draft.is_user_edited and draft.generation_status != GenerationStatus.DRAFT:
        draft.generation_status = GenerationStatus.MANUALLY_EDITED

    draft.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(draft)

    return _format_draft_response(draft)


@router.post("/drafts/{draft_id}/generate", response_model=OutreachDraftResponse)
def regenerate_outreach_draft(
    draft_id: str,
    payload: Optional[OutreachGenerateRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Regenerates draft content using the AI generator.
    Safely archives any previous user edits into context_snapshot['previous_revisions']
    so prior work is never lost.
    """
    draft = (
        db.query(OutreachDraft)
        .filter(OutreachDraft.id == draft_id, OutreachDraft.user_id == current_user.id)
        .first()
    )
    if not draft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Outreach draft not found or access denied."
        )

    # Archive existing version if non-empty
    snapshot = dict(draft.context_snapshot or {})
    revisions = snapshot.get("previous_revisions", [])
    if draft.body:
        revisions.append({
            "subject": draft.subject,
            "body": draft.body,
            "saved_at": draft.updated_at.isoformat() if draft.updated_at else datetime.now(timezone.utc).isoformat(),
            "was_user_edited": draft.is_user_edited
        })
        snapshot["previous_revisions"] = revisions

    # Apply override parameters if passed
    purpose = payload.purpose if payload and payload.purpose else draft.purpose
    recipient_type = payload.recipient_type if payload and payload.recipient_type else draft.recipient_type
    recipient_name = payload.recipient_name if payload and payload.recipient_name is not None else draft.recipient_name
    recipient_role = payload.recipient_role if payload and payload.recipient_role is not None else draft.recipient_role
    resume_id = payload.resume_id if payload and payload.resume_id is not None else draft.resume_id

    # Re-build grounded context
    try:
        context = OutreachContextBuilder.build_context(
            db=db,
            user_id=current_user.id,
            opportunity_id=draft.opportunity_id,
            resume_id=resume_id,
            recipient_name=recipient_name,
            recipient_role=recipient_role,
            purpose=purpose.value,
            recipient_type=recipient_type.value,
            existing_snapshot=draft.context_snapshot
        )
        context["previous_revisions"] = revisions
    except Exception as e:
        logger.error(f"Failed to re-build context for draft {draft_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # Generate
    try:
        draft_content = OutreachService.generate_draft_content(context)
    except Exception as e:
        logger.error(f"Failed to regenerate draft {draft_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"AI generation failed: {str(e)}"
        )

    # Update draft
    draft.purpose = purpose
    draft.recipient_type = recipient_type
    draft.recipient_name = recipient_name
    draft.recipient_role = recipient_role
    draft.resume_id = resume_id
    draft.subject = draft_content.get("subject", draft.subject)
    draft.body = draft_content.get("body", draft.body)
    draft.generation_status = draft_content.get("status", GenerationStatus.AI_GENERATED)
    draft.model_provider = draft_content.get("model_provider")
    draft.model_name = draft_content.get("model_name")
    draft.context_snapshot = context
    draft.is_user_edited = False
    draft.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(draft)

    return _format_draft_response(draft)


@router.delete("/drafts/{draft_id}", status_code=status.HTTP_200_OK)
def delete_outreach_draft(
    draft_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Deletes an outreach draft.
    Enforces user isolation: cannot delete another user's draft.
    """
    draft = (
        db.query(OutreachDraft)
        .filter(OutreachDraft.id == draft_id, OutreachDraft.user_id == current_user.id)
        .first()
    )
    if not draft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Outreach draft not found or access denied."
        )

    db.delete(draft)
    db.commit()

    return {"status": "deleted", "id": draft_id}
