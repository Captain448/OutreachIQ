from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class BaseAgentState(BaseModel):
    user_id: str
    run_id: str
    status: str = "initialized"
    evidence_trail: List[Dict[str, Any]] = Field(default_factory=list)
    uncertainty_score: float = 0.0
    errors: List[str] = Field(default_factory=list)


class AgentExecutionResult(BaseModel):
    success: bool
    agent_name: str
    output_data: Dict[str, Any]
    evidence_grounding: List[str]
    confidence: float
    explainability_notes: str
