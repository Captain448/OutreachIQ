import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Boolean, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship

from app.db.session import Base


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    company_id = Column(String(36), ForeignKey("companies.id", ondelete="CASCADE"), nullable=True, index=True)
    company_name = Column(String(255), nullable=False, index=True)
    
    title = Column(String(255), nullable=False, index=True)
    normalized_title = Column(String(255), nullable=False, index=True)
    location = Column(String(255), nullable=True)
    is_remote = Column(Boolean, default=False, nullable=False)
    work_arrangement = Column(String(50), default="flexible", nullable=False)  # remote, hybrid, onsite
    employment_type = Column(String(50), default="full-time", nullable=False)   # full-time, contract, internship
    
    description = Column(Text, nullable=True)
    experience_required = Column(String(100), nullable=True)
    education_required = Column(String(100), nullable=True)
    
    primary_url = Column(String(1000), nullable=False, index=True)
    application_url = Column(String(1000), nullable=True)
    salary_range = Column(String(100), nullable=True)
    # Verification Engine Fields
    verification_status = Column(String(50), default="LISTING_FOUND_STATUS_UNVERIFIED", nullable=False, index=True)
    verification_details = Column(JSON, default=dict, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    last_verified_at = Column(DateTime(timezone=True), nullable=True)

    # List of all source URLs where this job was found (for deduplication provenance)
    source_urls = Column(JSON, default=list, nullable=False)
    posting_date = Column(String(50), nullable=True)
    date_discovered = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    source_name = Column(String(100), default="Web Search", nullable=False)  # e.g. "Tavily (LinkedIn)", "Exa", "JSearch"
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    company = relationship("Company", back_populates="jobs")
    requirements = relationship("JobRequirement", back_populates="job", cascade="all, delete-orphan")
    opportunities = relationship("Opportunity", back_populates="job", cascade="all, delete-orphan")
    evidence_records = relationship("Evidence", back_populates="job", cascade="all, delete-orphan")


class JobRequirement(Base):
    __tablename__ = "job_requirements"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    job_id = Column(String(36), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    
    requirement_type = Column(String(50), default="skill", nullable=False)  # skill, experience, education, domain
    description = Column(String(500), nullable=False)
    is_critical = Column(Boolean, default=False, nullable=False)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    job = relationship("Job", back_populates="requirements")
