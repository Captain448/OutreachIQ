from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.schemas.intelligence import CandidateIntelligenceRepresentation
from app.services.profile_intelligence import ProfileIntelligenceService

router = APIRouter(prefix="/profile/intelligence", tags=["Profile Intelligence"])


@router.get("", response_model=CandidateIntelligenceRepresentation)
def get_profile_intelligence(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns the evidence-grounded candidate intelligence representation,
    combining structured profile data with extracted resume inventory.
    Strictly differentiates between VERIFIED, INFERRED, and UNVERIFIED skills.
    """
    return ProfileIntelligenceService.generate_candidate_intelligence(db, current_user)
