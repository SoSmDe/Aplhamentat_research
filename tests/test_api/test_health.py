"""
Tests for health check endpoint and basic API functionality.

Phase 0 verification: Ensures FastAPI application starts correctly.
"""

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the FastAPI application."""
    return TestClient(app)


class TestHealthEndpoint:
    """Tests for the /health endpoint."""

    def test_health_returns_ok(self, client: TestClient) -> None:
        """Health endpoint should return status ok."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data

    def test_health_returns_version(self, client: TestClient) -> None:
        """Health endpoint should return the application version."""
        response = client.get("/health")
        data = response.json()
        assert data["version"] == "0.1.0"


class TestRootEndpoint:
    """Tests for the root / endpoint."""

    def test_root_returns_welcome(self, client: TestClient) -> None:
        """Root endpoint should return welcome message."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Ralph" in data["message"]

    def test_root_includes_docs_links(self, client: TestClient) -> None:
        """Root endpoint should include documentation links."""
        response = client.get("/")
        data = response.json()
        assert data["docs"] == "/docs"
        assert data["redoc"] == "/redoc"
        assert data["health"] == "/health"


class TestPackageImport:
    """Tests for package imports to verify Phase 0 bootstrap."""

    def test_src_package_imports(self) -> None:
        """The src package should be importable."""
        import src
        assert src.__version__ == "0.1.0"

    def test_subpackages_import(self) -> None:
        """All src subpackages should be importable."""
        import src.api
        import src.agents
        import src.orchestrator
        import src.tools
        import src.storage
        import src.config
        # If we get here without ImportError, packages are correctly set up

    def test_main_app_imports(self) -> None:
        """The main FastAPI app should be importable."""
        from main import app
        assert app.title == "Ralph Deep Research"
        assert app.version == "0.1.0"
