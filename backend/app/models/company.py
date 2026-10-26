import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Boolean, Float, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship

from app.db.session import Base


class Company(Base):
    __tablename__ = "companies"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    name = Column(String(255), nullable=False, index=True)
    domain = Column(String(255), nullable=True, index=True)
    website_url = Column(String(500), nullable=True)
    description = Column(Text, nullable=True)
    industry = Column(String(100), nullable=True)
    size_range = Column(String(50), nullable=True)
    classification = Column(String(50), default="unknown", nullable=False, index=True)
    headquarters = Column(String(255), nullable=True)
    
    # Growth & Hiring Signals (grounded, not fabricated)
    growth_signal_score = Column(Float, default=0.0, nullable=False)  # 0.0 - 1.0
    alignment_score = Column(Float, default=0.0, nullable=False)      # 0.0 - 1.0
    signals_summary = Column(Text, nullable=True)
    # JSON list of signal objects: {type, headline, date, evidence_url, confidence}
    signals_data = Column(JSON, default=list, nullable=False)
    
    # Explainable reasons to contact or wait
    why_contact = Column(Text, nullable=True)
    why_wait = Column(Text, nullable=True)
    has_advertised_openings = Column(Boolean, default=False, nullable=False)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    jobs = relationship("Job", back_populates="company", cascade="all, delete-orphan")
    contacts = relationship("Contact", back_populates="company", cascade="all, delete-orphan")
    opportunities = relationship("Opportunity", back_populates="company", cascade="all, delete-orphan")
    evidence_records = relationship("Evidence", back_populates="company", cascade="all, delete-orphan")


class Contact(Base):
    __tablename__ = "contacts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    company_id = Column(String(36), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    
    name = Column(String(255), nullable=False)
    role_or_title = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)  # Strictly null unless verified
    linkedin_url = Column(String(500), nullable=True)
    evidence_source = Column(String(500), nullable=True)
    confidence = Column(Float, default=1.0, nullable=False)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    company = relationship("Company", back_populates="contacts")
