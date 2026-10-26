from typing import TypedDict, List, Dict, Any
from langgraph.graph import StateGraph, END


class OpportunityAgentState(TypedDict):
    user_id: str
    run_id: str
    query_params: Dict[str, Any]
    raw_jobs: List[Dict[str, Any]]
    raw_companies: List[Dict[str, Any]]
    deduped_jobs: List[Dict[str, Any]]
    deduped_companies: List[Dict[str, Any]]
    matched_opportunities: List[Dict[str, Any]]
    evidence_records: List[Dict[str, Any]]
    status: str
    confidence: float


def query_providers_node(state: OpportunityAgentState) -> Dict[str, Any]:
    return {"status": "providers_queried"}


def normalize_and_deduplicate_node(state: OpportunityAgentState) -> Dict[str, Any]:
    return {"status": "normalized_and_deduplicated"}


def evaluate_company_signals_node(state: OpportunityAgentState) -> Dict[str, Any]:
    return {"status": "signals_evaluated"}


def candidate_matching_node(state: OpportunityAgentState) -> Dict[str, Any]:
    return {"status": "candidates_matched"}


def synthesize_evidence_node(state: OpportunityAgentState) -> Dict[str, Any]:
    return {"status": "evidence_synthesized", "confidence": 0.92}


def build_opportunity_agent_graph():
    """
    Constructs the LangGraph state machine for the Opportunity Intelligence Agent.
    Prepares for cross-opportunity optimization and critic/verification agents.
    """
    builder = StateGraph(OpportunityAgentState)
    
    builder.add_node("query_providers", query_providers_node)
    builder.add_node("normalize_and_dedup", normalize_and_deduplicate_node)
    builder.add_node("evaluate_signals", evaluate_company_signals_node)
    builder.add_node("candidate_matching", candidate_matching_node)
    builder.add_node("synthesize_evidence", synthesize_evidence_node)

    builder.set_entry_point("query_providers")
    builder.add_edge("query_providers", "normalize_and_dedup")
    builder.add_edge("normalize_and_dedup", "evaluate_signals")
    builder.add_edge("evaluate_signals", "candidate_matching")
    builder.add_edge("candidate_matching", "synthesize_evidence")
    builder.add_edge("synthesize_evidence", END)

    return builder.compile()


opportunity_intelligence_graph = build_opportunity_agent_graph()
