from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

from app.models.outreach import OutreachPurpose, RecipientType, GenerationStatus


class OutreachDraftCreate(BaseModel):
    opportunity_id: str = Field(..., description="ID of the candidate's persisted opportunity")
    resume_id: Optional[str] = Field(None, description="Optional ID of the resume to ground evidence from")
    purpose: OutreachPurpose = Field(default=OutreachPurpose.FULL_TIME_APPLICATION)
    recipient_type: RecipientType = Field(default=RecipientType.HIRING_MANAGER)
    recipient_name: Optional[str] = Field(None, max_length=255)
    recipient_role: Optional[str] = Field(None, max_length=255)
    generate_immediately: bool = Field(default=True, description="Whether to invoke AI generation upon creation")


class OutreachDraftUpdate(BaseModel):
    subject: Optional[str] = Field(None, max_length=500)
    body: Optional[str] = None
    purpose: Optional[OutreachPurpose] = None
    recipient_type: Optional[RecipientType] = None
    recipient_name: Optional[str] = Field(None, max_length=255)
    recipient_role: Optional[str] = Field(None, max_length=255)
    user_notes: Optional[str] = None


class OutreachGenerateRequest(BaseModel):
    purpose: Optional[OutreachPurpose] = None
    recipient_type: Optional[RecipientType] = None
    recipient_name: Optional[str] = Field(None, max_length=255)
    recipient_role: Optional[str] = Field(None, max_length=255)
    resume_id: Optional[str] = None


class OutreachDraftResponse(BaseModel):
    id: str
    user_id: str
    opportunity_id: Optional[str] = None
    resume_id: Optional[str] = None
    purpose: OutreachPurpose
    recipient_type: RecipientType
    recipient_name: Optional[str] = None
    recipient_role: Optional[str] = None
    subject: str
    body: str
    generation_status: GenerationStatus
    model_provider: Optional[str] = None
    model_name: Optional[str] = None
    context_snapshot: Dict[str, Any] = Field(default_factory=dict)
    is_user_edited: bool = False
    user_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    # Associated metadata for UI convenience
    job_title: Optional[str] = None
    company_name: Optional[str] = None
    job_location: Optional[str] = None
    application_url: Optional[str] = None
    is_verified_opening: Optional[bool] = None
    verification_status: Optional[str] = None

    model_config = {"from_attributes": True}


class OutreachDraftListResponse(BaseModel):
    items: List[OutreachDraftResponse]
    total: int


class EligibleOpportunitySummary(BaseModel):
    id: str
    job_title: str
    company_name: str
    location: Optional[str] = None
    match_score: float
    application_url: Optional[str] = None
    is_verified: bool
    verification_status: str
    matched_skills: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)
    created_at: datetime

    model_config = {"from_attributes": True}

