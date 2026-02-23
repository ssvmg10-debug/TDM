"""Pytest fixtures for TDM backend tests."""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """FastAPI test client."""
    from main import app
    return TestClient(app)


@pytest.fixture
def sample_test_case_content():
    """Sample test case content for workflow tests."""
    return """navigate to https://example.com/checkout
Enter email as test@example.com
Enter firstname as John
Enter lastname as Doe
fill all the required details
click on submit"""
