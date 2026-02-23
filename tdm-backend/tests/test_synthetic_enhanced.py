"""Unit tests for synthetic data generation."""
import pytest
from services.synthetic_enhanced import SyntheticDataGenerator


class TestTestCaseNeedsSyntheticData:
    """Tests for test_case_needs_synthetic_data."""

    def setup_method(self):
        self.gen = SyntheticDataGenerator()

    def test_fill_details_detected(self):
        content = "fill all the required details"
        needs, reason = self.gen.test_case_needs_synthetic_data(content)
        assert needs is True
        assert "fill" in reason.lower() or "details" in reason.lower()

    def test_enter_as_pattern_detected(self):
        content = "Enter email as test@example.com"
        needs, _ = self.gen.test_case_needs_synthetic_data(content)
        assert needs is True

    def test_navigation_only_not_detected(self):
        content = "click on shop now\nclick on add to cart"
        needs, reason = self.gen.test_case_needs_synthetic_data(content)
        assert needs is False
        assert "navigation" in reason.lower() or "click" in reason.lower()

    def test_empty_returns_false(self):
        needs, reason = self.gen.test_case_needs_synthetic_data("")
        assert needs is False
        assert "empty" in reason.lower()


class TestParseTestCaseContent:
    """Tests for _parse_test_case_content."""

    def setup_method(self):
        self.gen = SyntheticDataGenerator()

    def test_parses_enter_as_pattern(self):
        content = "Enter email as test@example.com in the email field"
        schema = self.gen._parse_test_case_content(content)
        assert schema.get("has_form_fields") is True
        assert "entities" in schema
        assert len(schema["entities"]) > 0

    def test_fill_required_details_fallback(self):
        content = "fill all the required details at checkout"
        schema = self.gen._parse_test_case_content(content)
        assert schema.get("has_form_fields") is True
        assert "checkout" in schema.get("entities", {})
