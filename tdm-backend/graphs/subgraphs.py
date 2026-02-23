"""
Modular LangGraph subgraphs — each step as a composable graph.
These can be invoked individually or composed in the main workflow.
"""
from typing import Dict, Any, Callable
from langgraph.graph import StateGraph, END


def create_discover_graph(run_fn: Callable) -> Any:
    """discover_graph: schema discovery from DB."""
    def node(state: Dict) -> Dict:
        return {"discover_result": run_fn(state)}
    g = StateGraph(dict)
    g.add_node("discover", node)
    g.set_entry_point("discover")
    g.add_edge("discover", END)
    return g.compile()


def create_pii_graph(run_fn: Callable) -> Any:
    """pii_graph: PII classification."""
    def node(state: Dict) -> Dict:
        return {"pii_result": run_fn(state)}
    g = StateGraph(dict)
    g.add_node("pii", node)
    g.set_entry_point("pii")
    g.add_edge("pii", END)
    return g.compile()


def create_subset_graph(run_fn: Callable) -> Any:
    """subset_graph: FK-aware subsetting."""
    def node(state: Dict) -> Dict:
        return {"subset_result": run_fn(state)}
    g = StateGraph(dict)
    g.add_node("subset", node)
    g.set_entry_point("subset")
    g.add_edge("subset", END)
    return g.compile()


def create_mask_graph(run_fn: Callable) -> Any:
    """mask_graph: PII masking."""
    def node(state: Dict) -> Dict:
        return {"mask_result": run_fn(state)}
    g = StateGraph(dict)
    g.add_node("mask", node)
    g.set_entry_point("mask")
    g.add_edge("mask", END)
    return g.compile()


def create_synthetic_graph(run_fn: Callable) -> Any:
    """synthetic_graph: synthetic data generation."""
    def node(state: Dict) -> Dict:
        return {"synthetic_result": run_fn(state)}
    g = StateGraph(dict)
    g.add_node("synthetic", node)
    g.set_entry_point("synthetic")
    g.add_edge("synthetic", END)
    return g.compile()


def create_provisioning_graph(run_fn: Callable) -> Any:
    """provisioning_graph: provision to target."""
    def node(state: Dict) -> Dict:
        return {"provision_result": run_fn(state)}
    g = StateGraph(dict)
    g.add_node("provision", node)
    g.set_entry_point("provision")
    g.add_edge("provision", END)
    return g.compile()


def create_schema_fusion_graph(run_fn: Callable) -> Any:
    """schema_fusion_graph: fuse UI + API + DB + domain schemas."""
    def node(state: Dict) -> Dict:
        return {"schema_fusion_result": run_fn(state)}
    g = StateGraph(dict)
    g.add_node("schema_fusion", node)
    g.set_entry_point("schema_fusion")
    g.add_edge("schema_fusion", END)
    return g.compile()


def create_quality_graph(run_fn: Callable) -> Any:
    """quality_graph: synthetic quality metrics."""
    def node(state: Dict) -> Dict:
        return {"quality_result": run_fn(state)}
    g = StateGraph(dict)
    g.add_node("quality", node)
    g.set_entry_point("quality")
    g.add_edge("quality", END)
    return g.compile()
