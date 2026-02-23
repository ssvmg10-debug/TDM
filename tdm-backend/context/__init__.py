"""TDM Global Context - powers decision-making and lineage across all workflow steps."""
from .job_context import JobContext, create_initial_context

__all__ = ["JobContext", "create_initial_context"]
