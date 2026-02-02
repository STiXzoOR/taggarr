"""Tests for FastAPI application factory."""

from fastapi.testclient import TestClient

from taggarr.api.app import create_app


class TestHealthEndpoint:
    """Tests for the health endpoint."""

    def test_health_endpoint_returns_ok(self) -> None:
        """GET /health returns {"status": "ok"}."""
        app = create_app()
        client = TestClient(app)

        response = client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestRootEndpoint:
    """Tests for the root endpoint."""

    def test_app_serves_root(self) -> None:
        """GET / returns 200."""
        app = create_app()
        client = TestClient(app)

        response = client.get("/")

        assert response.status_code == 200
