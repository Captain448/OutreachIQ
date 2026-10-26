from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from app.models.profile import SkillStatus, SkillSource


# --- Skill Schemas ---
class SkillBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    category: str = Field(default="technical", max_length=50)
    status: SkillStatus = SkillStatus.VERIFIED
    source: SkillSource = SkillSource.USER_INPUT
    evidence: Optional[str] = None
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0)


class SkillCreate(SkillBase):
    pass


class SkillRead(SkillBase):
    id: str
    profile_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Education Schemas ---
class EducationBase(BaseModel):
    institution: str = Field(..., min_length=1, max_length=255)
    degree: str = Field(..., min_length=1, max_length=255)
    field_of_study: Optional[str] = Field(None, max_length=255)
    start_year: Optional[int] = None
    graduation_year: Optional[int] = None
    grade_or_gpa: Optional[str] = Field(None, max_length=50)
    details: Optional[str] = None


class EducationCreate(EducationBase):
    pass


class EducationRead(EducationBase):
    id: str
    profile_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Work Experience Schemas ---
class WorkExperienceBase(BaseModel):
    company: str = Field(..., min_length=1, max_length=255)
    role: str = Field(..., min_length=1, max_length=255)
    location: Optional[str] = Field(None, max_length=255)
    start_date: Optional[str] = Field(None, max_length=50)
    end_date: Optional[str] = Field(None, max_length=50)
    is_current: bool = False
    description: Optional[str] = None
    technologies: List[str] = Field(default_factory=list)


class WorkExperienceCreate(WorkExperienceBase):
    pass


class WorkExperienceRead(WorkExperienceBase):
    id: str
    profile_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Project Schemas ---
class ProjectBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    technologies: List[str] = Field(default_factory=list)
    role_contribution: Optional[str] = None
    github_url: Optional[str] = Field(None, max_length=500)
    demo_url: Optional[str] = Field(None, max_length=500)


class ProjectCreate(ProjectBase):
    pass


class ProjectRead(ProjectBase):
    id: str
    profile_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Preferences Schemas ---
class PreferencesBase(BaseModel):
    desired_roles: List[str] = Field(default_factory=list)
    preferred_industries: List[str] = Field(default_factory=list)
    preferred_locations: List[str] = Field(default_factory=list)
    remote_preference: str = Field(default="flexible")  # "remote", "hybrid", "onsite", "flexible"
    experience_level: str = Field(default="mid")       # "entry", "mid", "senior", "lead", "executive"
    employment_preference: str = Field(default="full-time")  # "full-time", "contract", "internship", "part-time"


class PreferencesCreate(PreferencesBase):
    pass


class PreferencesRead(PreferencesBase):
    id: str
    profile_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Profile Schemas ---
class ProfileBase(BaseModel):
    headline: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    location: Optional[str] = Field(None, max_length=255)
    bio: Optional[str] = None
    links: Dict[str, Any] = Field(default_factory=dict)


class ProfileCreate(ProfileBase):
    pass


class ProfileUpdate(BaseModel):
    # Basic Info
    full_name: Optional[str] = None
    headline: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    bio: Optional[str] = None
    links: Optional[Dict[str, Any]] = None
    
    # Sub-entities (can be updated together or independently)
    preferences: Optional[PreferencesBase] = None
    education: Optional[List[EducationBase]] = None
    work_experience: Optional[List[WorkExperienceBase]] = None
    projects: Optional[List[ProjectBase]] = None
    skills: Optional[List[SkillBase]] = None


class ProfileRead(ProfileBase):
    id: str
    user_id: str
    full_name: Optional[str] = None
    email: Optional[str] = None
    
    preferences: Optional[PreferencesRead] = None
    education: List[EducationRead] = Field(default_factory=list)
    work_experience: List[WorkExperienceRead] = Field(default_factory=list)
    projects: List[ProjectRead] = Field(default_factory=list)
    skills: List[SkillRead] = Field(default_factory=list)
    
    completeness_score: Optional[int] = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
