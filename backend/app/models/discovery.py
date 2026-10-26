import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Integer, Float, ForeignKey, DateTime, JSON, Enum
from sqlalchemy.orm import relationship

from app.db.session import Base


class RunStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    run_type = Column(String(100), default="opportunity_discovery", nullable=False)
    status = Column(Enum(RunStatus, native_enum=False), default=RunStatus.QUEUED, nullable=False, index=True)
    
    # Audit trail details
    query_params = Column(JSON, default=dict, nullable=False)
    providers_queried = Column(JSON, default=list, nullable=False)
    providers_succeeded = Column(JSON, default=list, nullable=False)
    providers_failed = Column(JSON, default=list, nullable=False)  # [{provider, error}]
    
    # Metrics
    results_discovered_count = Column(Integer, default=0, nullable=False)
    results_deduplicated_count = Column(Integer, default=0, nullable=False)
    opportunities_created_count = Column(Integer, default=0, nullable=False)
    execution_time_seconds = Column(Float, default=0.0, nullable=False)
    error_summary = Column(Text, nullable=True)
    # Internal source coverage diagnostics
    diagnostics = Column(JSON, default=dict, nullable=False)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    opportunities = relationship("Opportunity", back_populates="discovery_run")
