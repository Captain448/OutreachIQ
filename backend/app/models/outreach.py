import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Boolean, ForeignKey, DateTime, JSON, Enum
from sqlalchemy.orm import relationship

from app.db.session import Base


class OutreachPurpose(str, enum.Enum):
    INTERNSHIP_APPLICATION = "internship_application"
    FULL_TIME_APPLICATION = "full_time_application"
    RECRUITER_INTRODUCTION = "recruiter_introduction"
    REFERRAL_REQUEST = "referral_request"
    FOLLOW_UP = "follow_up"


class RecipientType(str, enum.Enum):
    HIRING_MANAGER = "hiring_manager"
    RECRUITER = "recruiter"
    PEER_ENGINEER = "peer_engineer"
    ALUMNUS_REFERRAL = "alumnus_referral"
    GENERAL_HR = "general_hr"


class GenerationStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    AI_GENERATED = "AI_GENERATED"
    MANUALLY_EDITED = "MANUALLY_EDITED"
    FAILED = "FAILED"


class OutreachDraft(Base):
    __tablename__ = "outreach_drafts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    opportunity_id = Column(String(36), ForeignKey("opportunities.id", ondelete="SET NULL"), nullable=True, index=True)
    resume_id = Column(String(36), ForeignKey("resumes.id", ondelete="SET NULL"), nullable=True, index=True)

    purpose = Column(
        Enum(OutreachPurpose, native_enum=False),
        default=OutreachPurpose.FULL_TIME_APPLICATION,
        nullable=False,
        index=True
    )
    recipient_type = Column(
        Enum(RecipientType, native_enum=False),
        default=RecipientType.HIRING_MANAGER,
        nullable=False,
        index=True
    )
    recipient_name = Column(String(255), nullable=True)
    recipient_role = Column(String(255), nullable=True)

    subject = Column(String(500), nullable=False, default="")
    body = Column(Text, nullable=False, default="")

    generation_status = Column(
        Enum(GenerationStatus, native_enum=False),
        default=GenerationStatus.DRAFT,
        nullable=False,
        index=True
    )
    model_provider = Column(String(50), nullable=True)
    model_name = Column(String(100), nullable=True)

    # Immutable context snapshot for reproducibility
    context_snapshot = Column(JSON, default=dict, nullable=False)
    is_user_edited = Column(Boolean, default=False, nullable=False)
    user_notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    user = relationship("User", back_populates="outreach_drafts")
    opportunity = relationship("Opportunity")
    resume = relationship("Resume")
    sent_messages = relationship("OutreachEmailMessage", back_populates="draft")

    def __repr__(self) -> str:
        return f"<OutreachDraft id={self.id} user_id={self.user_id} purpose={self.purpose}>"
