from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class ContactRead(BaseModel):
    id: str
    company_id: str
    name: str
    role_or_title: Optional[str] = None
    email: Optional[str] = None
    linkedin_url: Optional[str] = None
    evidence_source: Optional[str] = None
    confidence: float = 1.0
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CompanySignal(BaseModel):
    signal_type: str        # e.g., "tech_stack", "product_launch", "funding_expansion", "hiring_need"
    headline: str
    date: Optional[str] = None
    evidence_url: Optional[str] = None
    excerpt: Optional[str] = None
    confidence: float = 1.0


class CompanyRead(BaseModel):
    id: str
    name: str
    domain: Optional[str] = None
    website_url: Optional[str] = None
    description: Optional[str] = None
    industry: Optional[str] = None
    size_range: Optional[str] = None
    classification: Optional[str] = "unknown"
    headquarters: Optional[str] = None
    growth_signal_score: float = 0.0
    alignment_score: float = 0.0
    signals_summary: Optional[str] = None
    signals_data: List[Dict[str, Any]] = Field(default_factory=list)
    why_contact: Optional[str] = None
    why_wait: Optional[str] = None
    has_advertised_openings: bool = False
    contacts: List[ContactRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
