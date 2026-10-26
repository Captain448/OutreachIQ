import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Float, Integer, ForeignKey, DateTime, JSON, Enum
from sqlalchemy.orm import relationship

from app.db.session import Base


class CosgoProgressState(str, enum.Enum):
    RECOMMENDED = "RECOMMENDED"
    PLANNED = "PLANNED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


class CosgoRun(Base):
    __tablename__ = "cosgo_runs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Budget parameters (in hours)
    budget_hours = Column(Float, default=40.0, nullable=False)
    weekly_budget_hours = Column(Float, default=10.0, nullable=False)
    target_roles = Column(JSON, default=list, nullable=False)
    algorithm_version = Column(String(50), default="cosgo-v1.0", nullable=False)
    status = Column(String(50), default="completed", nullable=False)

    # Opportunity dataset accounting
    total_opportunities_analyzed = Column(Integer, default=0, nullable=False)
    eligible_opportunities_count = Column(Integer, default=0, nullable=False)
    excluded_opportunities_count = Column(Integer, default=0, nullable=False)

    # Coverage metrics (percentages stored as 0.0 - 1.0)
    baseline_coverage = Column(Float, default=0.0, nullable=False)
    projected_coverage = Column(Float, default=0.0, nullable=False)
    marginal_coverage_increase = Column(Float, default=0.0, nullable=False)

    # Opportunities meeting candidate qualification threshold (e.g. >= 75% coverage)
    opportunities_at_threshold_baseline = Column(Integer, default=0, nullable=False)
    opportunities_at_threshold_projected = Column(Integer, default=0, nullable=False)

    # Detailed diagnostics and exclusion breakdown
    diagnostics = Column(JSON, default=dict, nullable=False)
    opportunity_weights_used = Column(JSON, default=dict, nullable=False)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    user = relationship("User", backref="cosgo_runs")
    actions = relationship(
        "CosgoAction",
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="CosgoAction.priority_rank"
    )


class CosgoAction(Base):
    __tablename__ = "cosgo_actions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    run_id = Column(String(36), ForeignKey("cosgo_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Skill details
    skill_name = Column(String(100), nullable=False, index=True)
    category = Column(String(50), default="technical", nullable=False)
    priority_rank = Column(Integer, nullable=False)

    # Effort estimation and explicit uncertainty
    estimated_hours = Column(Float, nullable=False)
    effort_uncertainty_range = Column(JSON, default=dict, nullable=False)  # {"min": 10, "max": 18, "confidence": "high"}

    # Coverage contributions
    marginal_coverage_gain = Column(Float, nullable=False)
    cumulative_coverage = Column(Float, nullable=False)
    opportunities_count = Column(Integer, default=0, nullable=False)

    # Affected opportunities tracking
    target_opportunity_ids = Column(JSON, default=list, nullable=False)
    target_opportunities_summary = Column(JSON, default=list, nullable=False)

    # Prerequisites and justification
    prerequisites = Column(JSON, default=list, nullable=False)
    why_recommended = Column(Text, nullable=True)

    # Practical multi-skill project and verifiable learning resources
    practical_project = Column(JSON, default=dict, nullable=False)
    learning_resources = Column(JSON, default=list, nullable=False)

    # User-controlled progress tracking
    progress_state = Column(
        Enum(CosgoProgressState, native_enum=False),
        default=CosgoProgressState.RECOMMENDED,
        nullable=False,
        index=True
    )
    user_notes = Column(Text, nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    run = relationship("CosgoRun", back_populates="actions")
    user = relationship("User", backref="cosgo_actions")
