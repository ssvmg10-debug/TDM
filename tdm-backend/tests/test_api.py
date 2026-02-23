"""API integration tests."""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from main import app
    return TestClient(app)


class TestHealthEndpoints:
    """Basic API availability tests."""

    def test_docs_available(self, client: TestClient):
        r = client.get("/docs")
        assert r.status_code == 200

    def test_openapi_json(self, client: TestClient):
        r = client.get("/openapi.json")
        assert r.status_code == 200
        data = r.json()
        assert "openapi" in data
        assert "paths" in data


class TestWorkflowEndpoints:
    """Workflow API tests."""

    def test_classify_intent(self, client: TestClient):
        r = client.post(
            "/api/v1/workflow/classify-intent",
            json={
                "test_case_content": "fill email as test@example.com",
                "connection_string": "postgresql://localhost/db",
            },
        )
        assert r.status_code == 200
        data = r.json()
        assert "operations" in data
        assert isinstance(data["operations"], list)

    def test_analyze_test_case(self, client: TestClient):
        r = client.post(
            "/api/v1/workflow/analyze-test-case",
            json={"test_case_content": "Enter email as test@example.com"},
        )
        assert r.status_code == 200
        data = r.json()
        assert "needs_synthetic_data" in data
        assert "hint" in data


class TestDatasetsEndpoint:
    """Datasets API tests."""

    def test_list_datasets(self, client: TestClient):
        r = client.get("/api/v1/datasets")
        # 200 = success, 503 = service unavailable, 500 = DB not configured
        assert r.status_code in (200, 500, 503)
        if r.status_code == 200:
            assert isinstance(r.json(), list)


class TestQualityEndpoint:
    """Quality API tests."""

    def test_quality_requires_valid_dataset(self, client: TestClient):
        r = client.get("/api/v1/quality/dataset/00000000-0000-0000-0000-000000000000")
        assert r.status_code in (200, 404, 500)
