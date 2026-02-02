"""Integration tests for instance management."""


class TestInstanceFlow:
    """Test complete instance CRUD flow."""

    def test_instance_crud_flow(self, authenticated_client) -> None:
        """Test complete instance CRUD flow."""
        client = authenticated_client

        # Create instance
        response = client.post(
            "/api/v1/instance",
            json={
                "name": "Test Sonarr",
                "type": "sonarr",
                "url": "http://localhost:8989",
                "api_key": "test-api-key",
                "root_path": "/tv",
                "target_languages": ["en", "es"],
                "enabled": True,
            },
        )
        assert response.status_code == 201
        instance_id = response.json()["id"]
        assert response.json()["name"] == "Test Sonarr"
        assert response.json()["type"] == "sonarr"
        assert response.json()["target_languages"] == ["en", "es"]

        # List instances
        response = client.get("/api/v1/instance")
        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["name"] == "Test Sonarr"

        # Get instance
        response = client.get(f"/api/v1/instance/{instance_id}")
        assert response.status_code == 200
        assert response.json()["name"] == "Test Sonarr"
        assert response.json()["url"] == "http://localhost:8989"

        # Update instance
        response = client.put(
            f"/api/v1/instance/{instance_id}",
            json={"name": "Updated Sonarr"},
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Sonarr"
        # Other fields should be preserved
        assert response.json()["type"] == "sonarr"
        assert response.json()["target_languages"] == ["en", "es"]

        # Delete instance
        response = client.delete(f"/api/v1/instance/{instance_id}")
        assert response.status_code == 204

        # Verify deleted
        response = client.get("/api/v1/instance")
        assert len(response.json()) == 0

    def test_create_multiple_instances(self, authenticated_client) -> None:
        """Test creating multiple instances."""
        client = authenticated_client

        # Create Sonarr instance
        response = client.post(
            "/api/v1/instance",
            json={
                "name": "Sonarr",
                "type": "sonarr",
                "url": "http://localhost:8989",
                "api_key": "sonarr-key",
                "root_path": "/tv",
                "target_languages": ["en"],
            },
        )
        assert response.status_code == 201

        # Create Radarr instance
        response = client.post(
            "/api/v1/instance",
            json={
                "name": "Radarr",
                "type": "radarr",
                "url": "http://localhost:7878",
                "api_key": "radarr-key",
                "root_path": "/movies",
                "target_languages": ["en", "fr"],
            },
        )
        assert response.status_code == 201

        # List all instances
        response = client.get("/api/v1/instance")
        assert response.status_code == 200
        assert len(response.json()) == 2

    def test_instance_name_uniqueness(self, authenticated_client) -> None:
        """Test that instance names must be unique."""
        client = authenticated_client

        # Create first instance
        response = client.post(
            "/api/v1/instance",
            json={
                "name": "My Instance",
                "type": "sonarr",
                "url": "http://localhost:8989",
                "api_key": "key1",
                "root_path": "/tv",
            },
        )
        assert response.status_code == 201

        # Try to create instance with same name
        response = client.post(
            "/api/v1/instance",
            json={
                "name": "My Instance",
                "type": "radarr",
                "url": "http://localhost:7878",
                "api_key": "key2",
                "root_path": "/movies",
            },
        )
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    def test_get_nonexistent_instance(self, authenticated_client) -> None:
        """Test getting a nonexistent instance returns 404."""
        response = authenticated_client.get("/api/v1/instance/9999")
        assert response.status_code == 404
        assert response.json()["detail"] == "Instance not found"

    def test_update_nonexistent_instance(self, authenticated_client) -> None:
        """Test updating a nonexistent instance returns 404."""
        response = authenticated_client.put(
            "/api/v1/instance/9999",
            json={"name": "Updated"},
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "Instance not found"

    def test_delete_nonexistent_instance(self, authenticated_client) -> None:
        """Test deleting a nonexistent instance returns 404."""
        response = authenticated_client.delete("/api/v1/instance/9999")
        assert response.status_code == 404
        assert response.json()["detail"] == "Instance not found"

    def test_instance_test_connection(self, authenticated_client) -> None:
        """Test the connection test endpoint."""
        response = authenticated_client.post(
            "/api/v1/instance/test",
            json={
                "type": "sonarr",
                "url": "http://localhost:8989",
                "api_key": "test-key",
            },
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_instance_test_connection_invalid_url(
        self, authenticated_client
    ) -> None:
        """Test connection test with invalid URL."""
        response = authenticated_client.post(
            "/api/v1/instance/test",
            json={
                "type": "sonarr",
                "url": "not-a-valid-url",
                "api_key": "test-key",
            },
        )
        assert response.status_code == 200
        assert response.json()["success"] is False
        assert response.json()["message"] == "Invalid URL format"
