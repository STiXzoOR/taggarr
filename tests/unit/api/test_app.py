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


class TestCreateApp:
    """Tests for the create_app factory function."""

    def test_create_app_with_base_url(self) -> None:
        """create_app sets root_path for reverse proxy support."""
        app = create_app(base_url="/taggarr")
        assert app.root_path == "/taggarr"

        # Also verify root path stripping
        app2 = create_app(base_url="/taggarr/")
        assert app2.root_path == "/taggarr"
