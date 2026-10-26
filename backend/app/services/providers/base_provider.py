import abc
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class NormalizedJob(BaseModel):
    title: str
    company_name: str
    description: Optional[str] = None
    location: Optional[str] = None
    is_remote: bool = False
    work_arrangement: str = "flexible"
    employment_type: str = "full-time"
    primary_url: str
    application_url: Optional[str] = None
    salary_range: Optional[str] = None
    source_name: str
    source_provider: str
    source_category: str = "Job Board"
    posting_date: Optional[str] = None
    extracted_skills: List[str] = Field(default_factory=list)
    evidence_excerpt: Optional[str] = None
    confidence: float = 1.0
    extraction_quality: float = 1.0
    company_confidence: float = 1.0
    verification_status: str = "LISTING_FOUND_STATUS_UNVERIFIED"
    verification_details: Dict[str, Any] = Field(default_factory=dict)
    is_verified: bool = False
    last_verified_at: Optional[str] = None
    rejection_reason: Optional[str] = None


class CompanySignalItem(BaseModel):
    signal_type: str        # e.g., "tech_stack", "product_launch", "funding_expansion", "hiring_need"
    headline: str
    date: Optional[str] = None
    evidence_url: Optional[str] = None
    excerpt: Optional[str] = None
    confidence: float = 1.0


class NormalizedCompany(BaseModel):
    name: str
    domain: Optional[str] = None
    website_url: Optional[str] = None
    description: Optional[str] = None
    industry: Optional[str] = None
    headquarters: Optional[str] = None
    signals: List[CompanySignalItem] = Field(default_factory=list)
    source_name: str
    source_provider: str
    source_url: str
    evidence_excerpt: Optional[str] = None
    confidence: float = 1.0


class BaseProvider(abc.ABC):
    @property
    @abc.abstractmethod
    def provider_name(self) -> str:
        """Machine identifier (e.g. 'tavily', 'exa', 'jsearch')"""
        pass

    @property
    @abc.abstractmethod
    def display_name(self) -> str:
        """Human-readable display name"""
        pass

    @abc.abstractmethod
    def is_configured(self) -> bool:
        """Returns True if required API keys / credentials are set"""
        pass

    @abc.abstractmethod
    async def search_jobs(
        self,
        query: str,
        location: Optional[str] = None,
        remote_only: bool = False,
        limit: int = 20
    ) -> List[NormalizedJob]:
        """Discover advertised job openings"""
        pass

    @abc.abstractmethod
    async def search_companies(
        self,
        skills: List[str],
        industries: List[str],
        roles: List[str],
        locations: Optional[List[str]] = None,
        limit: int = 10
    ) -> List[NormalizedCompany]:
        """Discover potential company targets with public signals"""
        pass

    @abc.abstractmethod
    def get_health_status(self) -> Dict[str, Any]:
        """Returns provider availability, latency, error count, and quota status"""
        pass
