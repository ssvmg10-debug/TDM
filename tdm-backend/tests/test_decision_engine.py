"""Unit tests for the Dynamic Decision Engine."""
import pytest
from services.decision_engine import classify_intent, generate_pipeline_plan


class TestClassifyIntent:
    """Tests for classify_intent."""

    def test_connection_string_enables_discover_subset(self):
        intent = classify_intent(connection_string="postgresql://localhost/db")
        assert "discover" in intent["operations"]
        assert "subset" in intent["operations"]
        assert intent["requires_db"] is True

    def test_test_case_urls_enables_crawl(self):
        intent = classify_intent(test_case_urls=["https://example.com/form"])
        assert intent["requires_ui_crawl"] is True

    def test_test_case_content_with_fill_enables_synthetic(self):
        intent = classify_intent(test_case_content="fill email as test@example.com")
        assert "synthetic" in intent["operations"]

    def test_empty_input_returns_minimal_operations(self):
        intent = classify_intent()
        assert "operations" in intent
        assert isinstance(intent["operations"], list)

    def test_domain_fallback_when_no_schema(self):
        intent = classify_intent(domain="ecommerce", connection_string=None)
        assert intent.get("requires_domain_fallback") or "synthetic" in intent["operations"]


class TestGeneratePipelinePlan:
    """Tests for generate_pipeline_plan."""

    def test_plan_has_operations(self):
        intent = {"operations": ["discover", "pii", "subset"], "requires_db": True}
        plan = generate_pipeline_plan(intent)
        assert "operations" in plan
        assert plan["operations"] == ["discover", "pii", "subset"]

    def test_plan_includes_provision_when_dataset_expected(self):
        intent = {"operations": ["discover", "subset", "provision"], "requires_db": True}
        plan = generate_pipeline_plan(intent)
        assert "provision" in plan["operations"]
