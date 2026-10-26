from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from app.models.resume import ParsingStatus


class ResumeBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    target_role: str = Field(default="General", max_length=255)
    is_preferred: bool = False
    is_active: bool = True


class ResumeUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    target_role: Optional[str] = Field(None, max_length=255)
    is_preferred: Optional[bool] = None
    is_active: Optional[bool] = None


class ResumeRead(ResumeBase):
    id: str
    user_id: str
    filename: str
    original_filename: str
    file_size: int
    mime_type: str
    parsing_status: ParsingStatus
    parsing_confidence: float
    parsing_notes: Optional[str] = None
    parsed_text: Optional[str] = None
    extracted_skills: List[Dict[str, Any]] = Field(default_factory=list)
    extracted_education: List[Dict[str, Any]] = Field(default_factory=list)
    extracted_experience: List[Dict[str, Any]] = Field(default_factory=list)
    extracted_projects: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ResumeSummary(BaseModel):
    id: str
    title: str
    target_role: str
    is_preferred: bool
    is_active: bool
    original_filename: str
    file_size: int
    parsing_status: ParsingStatus
    parsing_confidence: float
    extracted_skills_count: int = 0
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
