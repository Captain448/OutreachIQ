import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship

from app.db.session import Base


class UserLearningPlan(Base):
    __tablename__ = "user_learning_plans"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)

    weekly_hours_budget = Column(Float, default=10.0, nullable=False)
    target_role = Column(String(255), nullable=True)

    completed_skills = Column(JSON, default=list, nullable=False)
    bookmarked_resources = Column(JSON, default=list, nullable=False)
    project_progress = Column(JSON, default=dict, nullable=False)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    user = relationship("User", back_populates="learning_plan")

    def __repr__(self) -> str:
        return f"<UserLearningPlan id={self.id} user_id={self.user_id} budget={self.weekly_hours_budget}>"
