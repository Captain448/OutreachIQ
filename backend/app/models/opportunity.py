import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Float, ForeignKey, DateTime, JSON, Enum
from sqlalchemy.orm import relationship

from app.db.session import Base


class OpportunityType(str, enum.Enum):
    ADVERTISED = "ADVERTISED"   # Concrete active opening verified
    EMERGING = "EMERGING"       # Credible signals suggest potential hiring need (no opening confirmed)
    STRATEGIC = "STRATEGIC"     # High alignment with candidate goals, proactive value hypothesis


class OpportunityStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    SAVED = "SAVED"
    DISMISSED = "DISMISSED"
    APPLIED = "APPLIED"


class RecommendedAction(str, enum.Enum):
    CONTACT_NOW = "CONTACT_NOW"       # High fit & adequate evidence
    IMPROVE_FIRST = "IMPROVE_FIRST"   # Promising opportunity, but key skills/portfolio gap exists
    SKIP = "SKIP"                     # Poor alignment, critical failure, or insufficient justification


class ClaimType(str, enum.Enum):
    OBSERVED_FACT = "OBSERVED_FACT"             # Directly scraped/verified from public source
    SYSTEM_INFERENCE = "SYSTEM_INFERENCE"       # Transparent deduction from verified signals
    UNKNOWN_INFORMATION = "UNKNOWN_INFORMATION" # Explicitly acknowledged missing information


class Opportunity(Base):
    __tablename__ = "opportunities"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id = Column(String(36), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=True, index=True)
    company_id = Column(String(36), ForeignKey("companies.id", ondelete="CASCADE"), nullable=True, index=True)
    discovery_run_id = Column(String(36), ForeignKey("agent_runs.id", ondelete="SET NULL"), nullable=True, index=True)
    
    opportunity_type = Column(Enum(OpportunityType, native_enum=False), default=OpportunityType.ADVERTISED, nullable=False, index=True)
    status = Column(Enum(OpportunityStatus, native_enum=False), default=OpportunityStatus.ACTIVE, nullable=False, index=True)
    
    # Heuristic scoring components (transparently separated, not pretending to be calibrated probabilities)
    match_score = Column(Float, default=0.0, nullable=False)            # 0.0 - 1.0
    evidence_confidence = Column(Float, default=0.8, nullable=False)    # 0.0 - 1.0
    extraction_quality = Column(Float, default=1.0, nullable=False)     # 0.0 - 1.0 (job extraction validity)
    company_confidence = Column(Float, default=1.0, nullable=False)     # 0.0 - 1.0 (employer identity resolution confidence)
    recommended_action = Column(Enum(RecommendedAction, native_enum=False), default=RecommendedAction.IMPROVE_FIRST, nullable=False, index=True)
    
    # Requirement and skill breakdown
    matched_skills = Column(JSON, default=list, nullable=False)
    missing_skills = Column(JSON, default=list, nullable=False)
    critical_failures = Column(JSON, default=list, nullable=False)
    explanation = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    job = relationship("Job", back_populates="opportunities")
    company = relationship("Company", back_populates="opportunities")
    evidence_items = relationship("Evidence", back_populates="opportunity", cascade="all, delete-orphan")
    discovery_run = relationship("AgentRun", back_populates="opportunities")


class Source(Base):
    __tablename__ = "sources"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    name = Column(String(255), nullable=False)          # e.g., "Tavily Web Search", "Exa Semantic Search"
    provider = Column(String(100), nullable=False)      # tavily, exa, jsearch, serpapi, adzuna, jooble
    url = Column(String(1000), nullable=False)
    retrieved_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    raw_content_preview = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    evidence_records = relationship("Evidence", back_populates="source")


class Evidence(Base):
    __tablename__ = "evidence"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    opportunity_id = Column(String(36), ForeignKey("opportunities.id", ondelete="CASCADE"), nullable=True, index=True)
    company_id = Column(String(36), ForeignKey("companies.id", ondelete="CASCADE"), nullable=True, index=True)
    job_id = Column(String(36), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=True, index=True)
    source_id = Column(String(36), ForeignKey("sources.id", ondelete="SET NULL"), nullable=True, index=True)
    
    claim_type = Column(Enum(ClaimType, native_enum=False), default=ClaimType.OBSERVED_FACT, nullable=False)
    claim_text = Column(Text, nullable=False)
    source_url = Column(String(1000), nullable=False)
    supporting_excerpt = Column(Text, nullable=True)
    confidence = Column(Float, default=1.0, nullable=False)
    retrieval_date = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    opportunity = relationship("Opportunity", back_populates="evidence_items")
    company = relationship("Company", back_populates="evidence_records")
    job = relationship("Job", back_populates="evidence_records")
    source = relationship("Source", back_populates="evidence_records")
