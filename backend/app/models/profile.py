import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Boolean, Integer, Float, ForeignKey, DateTime, JSON, Enum
from sqlalchemy.orm import relationship

from app.db.session import Base


class SkillStatus(str, enum.Enum):
    VERIFIED = "VERIFIED"        # Explicitly present in user profile or verified in resume
    INFERRED = "INFERRED"        # Strongly indicated by project/work experience evidence
    UNVERIFIED = "UNVERIFIED"    # Unconfirmed, should not be used as factual claim in outreach


class SkillSource(str, enum.Enum):
    USER_INPUT = "USER_INPUT"
    RESUME_PARSED = "RESUME_PARSED"
    EXPERIENCE_INFERRED = "EXPERIENCE_INFERRED"


class Profile(Base):
    __tablename__ = "profiles"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    
    # Basic Information
    headline = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    location = Column(String(255), nullable=True)
    bio = Column(Text, nullable=True)
    
    # Social / Professional Links (e.g. {"linkedin": "...", "github": "...", "portfolio": "..."})
    links = Column(JSON, default=dict, nullable=False)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    user = relationship("User", back_populates="profile")
    preferences = relationship("Preferences", back_populates="profile", uselist=False, cascade="all, delete-orphan")
    education = relationship("Education", back_populates="profile", cascade="all, delete-orphan", order_by="desc(Education.graduation_year)")
    work_experience = relationship("WorkExperience", back_populates="profile", cascade="all, delete-orphan", order_by="desc(WorkExperience.start_date)")
    projects = relationship("Project", back_populates="profile", cascade="all, delete-orphan")
    skills = relationship("Skill", back_populates="profile", cascade="all, delete-orphan")


class Preferences(Base):
    __tablename__ = "preferences"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    profile_id = Column(String(36), ForeignKey("profiles.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    
    # Lists stored as JSON arrays: ["Software Engineer", "ML Engineer"]
    desired_roles = Column(JSON, default=list, nullable=False)
    preferred_industries = Column(JSON, default=list, nullable=False)
    preferred_locations = Column(JSON, default=list, nullable=False)
    
    # Options: "remote", "hybrid", "onsite", "flexible"
    remote_preference = Column(String(50), default="flexible", nullable=False)
    # Options: "entry", "mid", "senior", "lead", "executive"
    experience_level = Column(String(50), default="mid", nullable=False)
    # Options: "full-time", "contract", "internship", "part-time"
    employment_preference = Column(String(50), default="full-time", nullable=False)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    profile = relationship("Profile", back_populates="preferences")


class Education(Base):
    __tablename__ = "education"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    profile_id = Column(String(36), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    
    institution = Column(String(255), nullable=False)
    degree = Column(String(255), nullable=False)
    field_of_study = Column(String(255), nullable=True)
    start_year = Column(Integer, nullable=True)
    graduation_year = Column(Integer, nullable=True)
    grade_or_gpa = Column(String(50), nullable=True)
    details = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    profile = relationship("Profile", back_populates="education")


class WorkExperience(Base):
    __tablename__ = "work_experience"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    profile_id = Column(String(36), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    
    company = Column(String(255), nullable=False)
    role = Column(String(255), nullable=False)
    location = Column(String(255), nullable=True)
    start_date = Column(String(50), nullable=True)  # e.g., "2022-01" or "Jan 2022"
    end_date = Column(String(50), nullable=True)    # e.g., "2024-03" or "Present"
    is_current = Column(Boolean, default=False, nullable=False)
    description = Column(Text, nullable=True)
    technologies = Column(JSON, default=list, nullable=False)  # JSON array of tech
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    profile = relationship("Profile", back_populates="work_experience")


class Project(Base):
    __tablename__ = "projects"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    profile_id = Column(String(36), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    technologies = Column(JSON, default=list, nullable=False)
    role_contribution = Column(Text, nullable=True)
    github_url = Column(String(500), nullable=True)
    demo_url = Column(String(500), nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    profile = relationship("Profile", back_populates="projects")


class Skill(Base):
    __tablename__ = "skills"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    profile_id = Column(String(36), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    
    name = Column(String(100), nullable=False, index=True)
    category = Column(String(50), default="technical", nullable=False)  # technical, tools, soft_skills, domain
    status = Column(Enum(SkillStatus, native_enum=False), default=SkillStatus.VERIFIED, nullable=False)
    source = Column(Enum(SkillSource, native_enum=False), default=SkillSource.USER_INPUT, nullable=False)
    evidence = Column(Text, nullable=True)  # Grounded quote/explanation of how this was identified
    confidence_score = Column(Float, default=1.0, nullable=False)  # 1.0 = definite fact
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    profile = relationship("Profile", back_populates="skills")
