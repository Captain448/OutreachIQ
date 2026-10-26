from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from app.models.opportunity import OpportunityType, OpportunityStatus, RecommendedAction, ClaimType
from app.models.discovery import RunStatus
from app.schemas.company import CompanyRead


class JobRequirementRead(BaseModel):
    id: str
    requirement_type: str
    description: str
    is_critical: bool

    model_config = ConfigDict(from_attributes=True)


class JobRead(BaseModel):
    id: str
    company_id: Optional[str] = None
    company_name: str
    title: str
    normalized_title: str
    location: Optional[str] = None
    is_remote: bool = False
    work_arrangement: str = "flexible"
    employment_type: str = "full-time"
    description: Optional[str] = None
    experience_required: Optional[str] = None
    education_required: Optional[str] = None
    primary_url: str
    application_url: Optional[str] = None
    salary_range: Optional[str] = None
    verification_status: str = "LISTING_FOUND_STATUS_UNVERIFIED"
    verification_details: Dict[str, Any] = Field(default_factory=dict)
    is_verified: bool = False
    last_verified_at: Optional[datetime] = None
    source_urls: List[str] = Field(default_factory=list)
    posting_date: Optional[str] = None
    date_discovered: datetime
    source_name: str
    requirements: List[JobRequirementRead] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class EvidenceRead(BaseModel):
    id: str
    claim_type: ClaimType
    claim_text: str
    source_url: str
    supporting_excerpt: Optional[str] = None
    confidence: float
    retrieval_date: datetime

    model_config = ConfigDict(from_attributes=True)


class OpportunityRead(BaseModel):
    id: str
    user_id: str
    opportunity_type: OpportunityType
    status: OpportunityStatus
    match_score: float
    evidence_confidence: float
    extraction_quality: float = 1.0
    company_confidence: float = 1.0
    recommended_action: RecommendedAction
    matched_skills: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)
    critical_failures: List[str] = Field(default_factory=list)
    explanation: Optional[str] = None
    
    # Nested relations
    job: Optional[JobRead] = None
    company: Optional[CompanyRead] = None
    evidence_items: List[EvidenceRead] = Field(default_factory=list)
    
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OpportunityStatusUpdate(BaseModel):
    status: OpportunityStatus


class DiscoveryRunRequest(BaseModel):
    target_roles: Optional[List[str]] = None
    skills: Optional[List[str]] = None
    industries: Optional[List[str]] = None
    locations: Optional[List[str]] = None
    remote_preference: Optional[str] = None
    work_arrangement: Optional[str] = None  # "Any", "remote", "hybrid", "onsite"
    employment_type: Optional[str] = None   # "Any", "internship", "full-time", "contract", "part-time"
    experience_level: Optional[str] = None  # "Any", "entry", "fresher", "mid", "senior"
    opportunity_type: Optional[str] = None  # None for ALL, or "ADVERTISED", "EMERGING", "STRATEGIC"
    limit: Optional[int] = Field(default=20, ge=1, le=50)


class DiscoveryRunRead(BaseModel):
    id: str
    user_id: str
    run_type: str
    status: RunStatus
    query_params: Dict[str, Any] = Field(default_factory=dict)
    providers_queried: List[str] = Field(default_factory=list)
    providers_succeeded: List[str] = Field(default_factory=list)
    providers_failed: List[Dict[str, Any]] = Field(default_factory=list)
    results_discovered_count: int = 0
    results_deduplicated_count: int = 0
    opportunities_created_count: int = 0
    execution_time_seconds: float = 0.0
    error_summary: Optional[str] = None
    diagnostics: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FilterSuggestionsRead(BaseModel):
    locations: List[str] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
