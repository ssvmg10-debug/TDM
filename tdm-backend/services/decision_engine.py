"""
Dynamic Decision Engine — Intent-aware pipeline planning.
Decides what to run based on user input, test cases, and schema availability.
"""
import re
import logging
from typing import Dict, List, Optional, Any

from context.job_context import JobContext

logger = logging.getLogger("tdm.decision")


# Intent output structure
INTENT_OPERATIONS = [
    "discover", "pii", "subset", "mask", "synthetic", "provision",
    "schema_fusion", "quality"
]

PREFERRED_SYNTHETIC_MODES = ["schema", "url", "test_case", "domain", "hybrid"]


def classify_intent(
    test_case_content: Optional[str] = None,
    test_case_urls: Optional[List[str]] = None,
    connection_string: Optional[str] = None,
    domain: Optional[str] = None,
    schema_version_id: Optional[str] = None,
    config_flags: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Intent classifier: determines what operations to run and synthetic mode.

    Rules:
    - If connection_string provided → enable discover + subset
    - If test case includes URLs → enable crawl (requires_ui_crawl)
    - If domain provided → enable domain-pack
    - If no schema found → enable domain fallback
    - If PII detected → auto-enable masking
    - If synthetic is needed → choose mode based on schemas available
    """
    config_flags = config_flags or {}
    intent = {
        "requires_ui_crawl": False,
        "requires_db": False,
        "requires_api": False,
        "requires_domain_fallback": False,
        "operations": [],
        "preferred_synthetic_mode": "schema",
    }

    # Rule: connection_string → discover + subset
    if connection_string:
        intent["requires_db"] = True
        if "discover" not in intent["operations"]:
            intent["operations"].append("discover")
        if "subset" in config_flags.get("operations", []) or config_flags.get("enable_subset", True):
            intent["operations"].append("subset")
        intent["operations"].append("pii")

    # Rule: test case URLs → enable crawl
    if test_case_urls and any(u.strip() for u in test_case_urls):
        intent["requires_ui_crawl"] = True
        if "synthetic" not in intent["operations"]:
            intent["operations"].append("synthetic")
        intent["preferred_synthetic_mode"] = "url"

    # Rule: domain provided → enable domain-pack
    if domain:
        if "synthetic" not in intent["operations"]:
            intent["operations"].append("synthetic")
        if not intent["requires_ui_crawl"] and not schema_version_id:
            intent["preferred_synthetic_mode"] = "domain"

    # Rule: test case content with form fields → test_case mode
    if test_case_content and _has_form_fields(test_case_content):
        if "synthetic" not in intent["operations"]:
            intent["operations"].append("synthetic")
        if not intent["requires_ui_crawl"]:
            intent["preferred_synthetic_mode"] = "test_case"

    # Rule: no schema found → domain fallback
    if not schema_version_id and not connection_string and (domain or test_case_content or test_case_urls):
        intent["requires_domain_fallback"] = True
        if "synthetic" not in intent["operations"]:
            intent["operations"].append("synthetic")
        intent["preferred_synthetic_mode"] = "hybrid" if (domain and (test_case_content or test_case_urls)) else "domain"

    # Rule: PII detection → auto-enable masking when we have schema
    if schema_version_id or connection_string:
        if "pii" not in intent["operations"]:
            intent["operations"].append("pii")
        intent["operations"].append("mask")

    # Always add provision if synthetic or subset
    if "synthetic" in intent["operations"] or "subset" in intent["operations"]:
        if "provision" not in intent["operations"]:
            intent["operations"].append("provision")

    # Deduplicate and order
    order = ["discover", "pii", "subset", "mask", "synthetic", "provision", "schema_fusion", "quality"]
    seen = set()
    ordered = []
    for op in order:
        if op in intent["operations"] and op not in seen:
            seen.add(op)
            ordered.append(op)
    for op in intent["operations"]:
        if op not in seen:
            seen.add(op)
            ordered.append(op)
    intent["operations"] = ordered

    logger.info(f"[DECISION] Intent: {intent}")
    return intent


def _has_form_fields(content: str) -> bool:
    """Detect if test case has form field patterns (Enter, fill, input, type)."""
    if not content or not content.strip():
        return False
    patterns = [
        r"\b(?:enter|fill|input|type)\s+[\"']?\w+[\"']?\s+as\s+",
        r"\b(?:enter|fill|input|type)\s+[\"'][^\"']+[\"']\s+in\s+",
        r"send_keys\s*\([^)]+\)",
        r"\.fill\s*\([^)]+\)",
        r"\.type\s*\([^)]+\)",
    ]
    content_lower = content.lower()
    for p in patterns:
        if re.search(p, content_lower, re.IGNORECASE):
            return True
    return False


def generate_pipeline_plan(
    intent: Dict[str, Any],
    context: Optional[JobContext] = None,
) -> Dict[str, Any]:
    """
    Generate pipeline plan from intent.
    Returns operations list and config hints.
    """
    plan = {
        "operations": intent.get("operations", []),
        "preferred_synthetic_mode": intent.get("preferred_synthetic_mode", "schema"),
        "requires_ui_crawl": intent.get("requires_ui_crawl", False),
        "requires_db": intent.get("requires_db", False),
        "requires_domain_fallback": intent.get("requires_domain_fallback", False),
        "config_hints": {},
    }

    if plan["requires_ui_crawl"]:
        plan["config_hints"]["synthetic"] = {"mode": "url", "crawl_first": True}
    if plan["requires_domain_fallback"]:
        plan["config_hints"]["synthetic"] = plan["config_hints"].get("synthetic", {})
        plan["config_hints"]["synthetic"]["use_domain_fallback"] = True

    return plan
