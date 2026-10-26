from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class CosgoOptimizeRequest(BaseModel):
    budget_hours: Optional[float] = Field(default=40.0, ge=5.0, le=300.0, description="Total learning time budget in hours")
    weekly_budget_hours: Optional[float] = Field(default=10.0, ge=2.0, le=60.0, description="Weekly study time budget in hours")
    target_roles: Optional[List[str]] = Field(default=None, description="Optional target roles override. Defaults to profile desired roles.")
    min_opportunity_relevance: Optional[float] = Field(default=0.35, ge=0.0, le=1.0, description="Filter cutoff for opportunity relevance")


class CosgoActionUpdateProgressRequest(BaseModel):
    progress_state: str = Field(description="New progress state: RECOMMENDED, PLANNED, IN_PROGRESS, COMPLETED")
    user_notes: Optional[str] = Field(default=None, description="User learning notes, progress summary, or reflection")


class CosgoBudgetUpdateRequest(BaseModel):
    budget_hours: float = Field(ge=5.0, le=300.0, description="Updated total hours budget")
    weekly_budget_hours: Optional[float] = Field(default=None, ge=2.0, le=60.0, description="Updated weekly hours budget")


class PracticalProjectSchema(BaseModel):
    title: str
    description: str
    overlapping_skills: List[str]
    deliverables: List[str]
    difficulty_level: str = "Intermediate"


class LearningResourceSchema(BaseModel):
    title: str
    url: str
    provider: str
    is_verified: bool = True
    resource_type: str = "Documentation & Tutorial"


class CosgoActionResponse(BaseModel):
    id: str
    run_id: str
    user_id: str
    skill_name: str
    category: str
    priority_rank: int
    estimated_hours: float
    effort_uncertainty_range: Dict[str, Any] = {}
    marginal_coverage_gain: float
    cumulative_coverage: float
    opportunities_count: int
    target_opportunity_ids: List[str] = []
    target_opportunities_summary: List[Dict[str, Any]] = []
    prerequisites: List[str] = []
    why_recommended: Optional[str] = None
    practical_project: Dict[str, Any] = {}
    learning_resources: List[Dict[str, Any]] = []
    progress_state: str
    user_notes: Optional[str] = None
    completed_at: Optional[str] = None
    created_at: str

    model_config = {"from_attributes": True}


class CosgoRunResponse(BaseModel):
    id: str
    user_id: str
    budget_hours: float
    weekly_budget_hours: float
    target_roles: List[str] = []
    algorithm_version: str
    status: str
    total_opportunities_analyzed: int
    eligible_opportunities_count: int
    excluded_opportunities_count: int
    baseline_coverage: float
    projected_coverage: float
    marginal_coverage_increase: float
    opportunities_at_threshold_baseline: int
    opportunities_at_threshold_projected: int
    diagnostics: Dict[str, Any] = {}
    actions: List[CosgoActionResponse] = []
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class CoverageMatrixItem(BaseModel):
    opportunity_id: str
    job_title: str
    company_name: str
    match_score: float
    role_relevance: float
    requirements: List[str]
    verified_skills: List[str]
    inferred_skills: List[str]
    actions_covering: List[str]
    remaining_gaps: List[str]
    baseline_coverage: float
    projected_coverage: float


class CosgoCoverageMatrixResponse(BaseModel):
    run_id: str
    total_skills_count: int
    skills_header: List[str]
    matrix: List[CoverageMatrixItem]
    skill_frequency: Dict[str, int]


class CosgoBenchmarkResponse(BaseModel):
    dataset_summary: Dict[str, Any]
    cosgo: Dict[str, Any]
    frequency_baseline: Dict[str, Any]
    independent_per_job: Dict[str, Any]
    greedy_frequency_no_effort: Dict[str, Any]
    exact_oracle: Optional[Dict[str, Any]] = None
    comparison_summary: Dict[str, Any]
    experiment_type: Optional[str] = None
    sensitivity_note: Optional[str] = None
    canonical_budget_utilization_note: Optional[str] = None
