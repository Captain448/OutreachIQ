from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.schemas.profile import ProfileRead, ProfileUpdate
from app.services.profile_service import ProfileService

router = APIRouter(prefix="/profile", tags=["Profile"])


@router.get("", response_model=ProfileRead)
def get_user_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    profile = ProfileService.get_or_create_profile(db, current_user)
    completeness = ProfileService.calculate_completeness(profile, current_user)
    
    # Enrich response with user info
    res = ProfileRead.model_validate(profile)
    res.full_name = current_user.full_name
    res.email = current_user.email
    res.completeness_score = completeness
    return res


@router.put("", response_model=ProfileRead)
def update_user_profile(
    update_data: ProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    profile = ProfileService.update_profile(db, current_user, update_data)
    completeness = ProfileService.calculate_completeness(profile, current_user)
    
    res = ProfileRead.model_validate(profile)
    res.full_name = current_user.full_name
    res.email = current_user.email
    res.completeness_score = completeness
    return res
