from typing import List
from fastapi import APIRouter, Depends
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.provider import ProviderHealthRead
from app.services.providers.provider_registry import provider_registry

router = APIRouter(prefix="/providers", tags=["Providers & Health"])


@router.get("/health", response_model=List[ProviderHealthRead])
def get_providers_health(current_user: User = Depends(get_current_user)):
    """
    Returns the operational and configuration status of all research & job discovery providers.
    """
    statuses = provider_registry.get_all_health_statuses()
    return [ProviderHealthRead.model_validate(s) for s in statuses]
