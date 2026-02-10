"""Integration tests for authentication flow."""


class TestAuthFlow:
    """Test complete authentication lifecycle."""

    def test_full_auth_lifecycle(self, client) -> None:
        """Test complete auth flow: initialize -> login -> status -> logout."""
        # Check not initialized
        response = client.get("/api/v1/auth/status")
        assert response.status_code == 200
        assert response.json()["initialized"] is False

        # Initialize
        response = client.post(
            "/api/v1/initialize",
            json={"username": "admin", "password": "password123"},
        )
        assert response.status_code == 200
        assert response.json()["message"] == "System initialized successfully"

        # Now initialized and logged in
        response = client.get("/api/v1/auth/status")
        assert response.json()["initialized"] is True
        assert response.json()["authenticated"] is True
        assert response.json()["user"]["username"] == "admin"

        # Logout
        response = client.post("/api/v1/auth/logout")
        assert response.status_code == 200
        assert response.json()["message"] == "Logout successful"

        # Verify logged out
        response = client.get("/api/v1/auth/status")
        assert response.json()["authenticated"] is False
        assert response.json()["initialized"] is True

        # Login again
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "password123"},
        )
        assert response.status_code == 200
        assert response.json()["message"] == "Login successful"

        # Verify authenticated
        response = client.get("/api/v1/auth/status")
        assert response.json()["authenticated"] is True

    def test_cannot_reinitialize(self, client) -> None:
        """Test that system cannot be initialized twice."""
        # First initialization
        response = client.post(
            "/api/v1/initialize",
            json={"username": "admin", "password": "password123"},
        )
        assert response.status_code == 200

        # Second initialization should fail
        response = client.post(
            "/api/v1/initialize",
            json={"username": "admin2", "password": "password456"},
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "System already initialized"

    def test_login_with_wrong_password(self, authenticated_client) -> None:
        """Test login failure with wrong password."""
        # Logout first
        authenticated_client.post("/api/v1/auth/logout")

        # Try wrong password
        response = authenticated_client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "wrongpassword"},
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid username or password"

    def test_login_with_nonexistent_user(self, authenticated_client) -> None:
        """Test login failure with nonexistent user."""
        # Logout first
        authenticated_client.post("/api/v1/auth/logout")

        # Try nonexistent user
        response = authenticated_client.post(
            "/api/v1/auth/login",
            json={"username": "nonexistent", "password": "password123"},
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid username or password"

    def test_protected_endpoint_requires_auth(self, client) -> None:
        """Test that protected endpoints require authentication."""
        # Initialize but don't login
        client.post(
            "/api/v1/initialize",
            json={"username": "admin", "password": "password123"},
        )
        client.post("/api/v1/auth/logout")

        # Try to access protected endpoint
        response = client.get("/api/v1/instance")
        assert response.status_code == 401
        assert response.json()["detail"] == "Not authenticated"
