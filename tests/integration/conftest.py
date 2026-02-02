"""Integration test fixtures."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from taggarr.server import create_server


@pytest.fixture
def app(tmp_path: Path):
    """Create app with real SQLite database.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        Configured FastAPI application with SQLite database.
    """
    db_path = tmp_path / "test.db"
    return create_server(db_path=db_path)


@pytest.fixture
def client(app):
    """Create test client.

    Args:
        app: FastAPI application instance.

    Returns:
        TestClient for making requests to the app.
    """
    return TestClient(app)


@pytest.fixture
def authenticated_client(client):
    """Create authenticated test client.

    Initializes the system with an admin user and returns
    a client that is logged in.

    Args:
        client: Base test client.

    Returns:
        TestClient with authenticated session cookie.
    """
    # Initialize system
    client.post(
        "/api/v1/initialize",
        json={"username": "admin", "password": "password123"},
    )
    return client
