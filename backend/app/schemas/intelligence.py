from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from app.models.profile import SkillStatus


class CategorizedSkill(BaseModel):
    name: str
    category: str
    status: SkillStatus  # VERIFIED, INFERRED, UNVERIFIED
    source: str          # e.g., "Profile Direct", "Resume: AI/ML", "Inferred from Project"
    evidence: Optional[str] = None
    confidence_score: float = 1.0


class CareerDirectionSummary(BaseModel):
    target_role: str
    associated_resumes: List[str]
    matching_skills: List[str]
    readiness_level: str  # e.g., "High", "Moderate", "Emerging"
    evidence_notes: str


class CompletenessMetric(BaseModel):
    overall_percentage: int
    missing_critical_fields: List[str]
    recommendations: List[str]


class CandidateIdentity(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    headline: Optional[str] = None
    links: Dict[str, Any] = Field(default_factory=dict)


class CandidateIntelligenceRepresentation(BaseModel):
    identity: CandidateIdentity
    education: List[Dict[str, Any]]
    work_experience: List[Dict[str, Any]]
    projects: List[Dict[str, Any]]
    
    # Strictly segregated skills
    verified_skills: List[CategorizedSkill]
    inferred_skills: List[CategorizedSkill]
    unverified_skills: List[CategorizedSkill]
    
    preferences: Dict[str, Any]
    resume_inventory: List[Dict[str, Any]]
    career_directions: List[CareerDirectionSummary]
    profile_completeness: CompletenessMetric
    overall_confidence: float
    evidence_grounding_summary: str
