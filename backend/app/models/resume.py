import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Boolean, Integer, Float, ForeignKey, DateTime, JSON, Enum
from sqlalchemy.orm import relationship

from app.db.session import Base


class ParsingStatus(str, enum.Enum):
    PENDING = "pending"
    PARSED = "parsed"
    PARTIAL = "partial"
    FAILED = "failed"


class Resume(Base):
    __tablename__ = "resumes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Metadata & Customization
    title = Column(String(255), nullable=False)  # e.g. "Software Developer Resume", "AI/ML Resume"
    target_role = Column(String(255), default="General", nullable=False)  # e.g. "Frontend", "Backend", "ML"
    is_preferred = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Physical File Details
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String(100), nullable=False)
    
    # Parsing Results (Evidence-grounded, never fabricated)
    parsed_text = Column(Text, nullable=True)
    parsing_status = Column(Enum(ParsingStatus, native_enum=False), default=ParsingStatus.PENDING, nullable=False)
    parsing_confidence = Column(Float, default=1.0, nullable=False)  # 0.0 - 1.0
    parsing_notes = Column(Text, nullable=True)                      # Explainability for parsing issues/uncertainty
    
    # Structured Extracted Information
    extracted_skills = Column(JSON, default=list, nullable=False)
    extracted_education = Column(JSON, default=list, nullable=False)
    extracted_experience = Column(JSON, default=list, nullable=False)
    extracted_projects = Column(JSON, default=list, nullable=False)
    raw_metadata = Column(JSON, default=dict, nullable=False)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    user = relationship("User", back_populates="resumes")
