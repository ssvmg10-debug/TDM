"""
Decision Graph — LangGraph subgraph for intent classification and pipeline planning.
Node sequence: parse_user_input → classify_intent → generate_pipeline_plan → output operations[]
"""
from typing import Dict, Any, TypedDict, Optional, List

from langgraph.graph import StateGraph, END

from services.decision_engine import classify_intent, generate_pipeline_plan
from context.job_context import JobContext


class DecisionState(TypedDict, total=False):
    """State for decision graph."""
    test_case_content: Optional[str]
    test_case_urls: Optional[List[str]]
    connection_string: Optional[str]
    domain: Optional[str]
    schema_version_id: Optional[str]
    config_flags: Dict[str, Any]
    intent: Dict[str, Any]
    plan: Dict[str, Any]
    operations: List[str]


def _parse_user_input(state: DecisionState) -> DecisionState:
    """Parse and normalize user input (placeholder for future NLP)."""
    return state


def _classify_intent_node(state: DecisionState) -> DecisionState:
    """Run intent classifier."""
    intent = classify_intent(
        test_case_content=state.get("test_case_content"),
        test_case_urls=state.get("test_case_urls"),
        connection_string=state.get("connection_string"),
        domain=state.get("domain"),
        schema_version_id=state.get("schema_version_id"),
        config_flags=state.get("config_flags"),
    )
    return {**state, "intent": intent}


def _generate_plan_node(state: DecisionState) -> DecisionState:
    """Generate pipeline plan from intent."""
    plan = generate_pipeline_plan(
        intent=state.get("intent", {}),
        context=None,
    )
    return {
        **state,
        "plan": plan,
        "operations": plan.get("operations", []),
    }


def create_decision_graph():
    """Build decision_graph: parse → classify → plan → output."""
    workflow = StateGraph(DecisionState)

    workflow.add_node("parse_user_input", _parse_user_input)
    workflow.add_node("classify_intent", _classify_intent_node)
    workflow.add_node("generate_pipeline_plan", _generate_plan_node)

    workflow.set_entry_point("parse_user_input")
    workflow.add_edge("parse_user_input", "classify_intent")
    workflow.add_edge("classify_intent", "generate_pipeline_plan")
    workflow.add_edge("generate_pipeline_plan", END)

    return workflow.compile()
