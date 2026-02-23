"""
Workflow Graph — Main LangGraph that composes modular subgraphs.
Orchestrates: decision → discover → pii → subset → mask → synthetic → provisioning
With optional: schema_fusion, quality
"""
from typing import Dict, Any, TypedDict, Optional, List
import logging

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from graphs.decision_graph import create_decision_graph

logger = logging.getLogger("tdm.graph")


class WorkflowState(TypedDict, total=False):
    """State passed through workflow graph."""
    # Input
    test_case_content: Optional[str]
    test_case_urls: Optional[List[str]]
    connection_string: Optional[str]
    domain: Optional[str]
    schema_version_id: Optional[str]
    dataset_version_id: Optional[str]
    config: Dict[str, Any]
    job_id: Optional[str]
    workflow_id: Optional[str]

    # Decision output
    operations: List[str]
    intent: Dict[str, Any]
    plan: Dict[str, Any]

    # Step results
    discover_result: Dict[str, Any]
    pii_result: Dict[str, Any]
    subset_result: Dict[str, Any]
    mask_result: Dict[str, Any]
    synthetic_result: Dict[str, Any]
    provision_result: Dict[str, Any]
    schema_fusion_result: Dict[str, Any]
    quality_result: Dict[str, Any]

    # Final
    overall_status: str
    error: Optional[str]


def _run_decision(state: WorkflowState) -> WorkflowState:
    """Run decision graph to get operations list."""
    dg = create_decision_graph()
    init = {
        "test_case_content": state.get("test_case_content"),
        "test_case_urls": state.get("test_case_urls"),
        "connection_string": state.get("connection_string"),
        "domain": state.get("domain"),
        "schema_version_id": state.get("schema_version_id"),
        "config_flags": state.get("config", {}),
    }
    result = dg.invoke(init)
    return {
        **state,
        "operations": result.get("operations", []),
        "intent": result.get("intent", {}),
        "plan": result.get("plan", {}),
    }


def _router_after_decision(state: WorkflowState) -> str:
    """Route to first operation. For now we use the legacy orchestrator for execution."""
    return "end"  # Decision graph output is used by orchestrator; we don't run steps in graph yet


def create_workflow_graph():
    """
    Build main workflow graph.
    Currently: decision_graph only. Step execution remains in WorkflowOrchestrator
    for backward compatibility. Can be extended to run each step as a graph node.
    """
    workflow = StateGraph(WorkflowState)

    workflow.add_node("decision", _run_decision)
    workflow.add_node("end", lambda s: s)  # Placeholder

    workflow.set_entry_point("decision")
    workflow.add_conditional_edges("decision", _router_after_decision, {"end": "end"})
    workflow.add_edge("end", END)

    return workflow.compile(checkpointer=MemorySaver())
