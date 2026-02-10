"""Integration tests for media operations."""

import json
from datetime import datetime

from taggarr.db import Media, Season


class TestMediaFlow:
    """Test media operations flow."""

    def test_list_media_empty(self, authenticated_client) -> None:
        """Test listing media when empty."""
        response = authenticated_client.get("/api/v1/media")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["page"] == 1

    def test_media_pagination(self, authenticated_client, app) -> None:
        """Test media list pagination."""
        client = authenticated_client

        # Create instance first
        response = client.post(
            "/api/v1/instance",
            json={
                "name": "Test Sonarr",
                "type": "sonarr",
                "url": "http://localhost:8989",
                "api_key": "test-key",
                "root_path": "/tv",
            },
        )
        instance_id = response.json()["id"]

        # Add media directly to database
        from taggarr.db import get_session

        with get_session(app.state.db_engine) as db:
            for i in range(15):
                media = Media(
                    instance_id=instance_id,
                    title=f"Test Show {i}",
                    clean_title=f"test-show-{i}",
                    path=f"/tv/test-show-{i}",
                    media_type="series",
                    added=datetime.now(),
                )
                db.add(media)
            db.commit()

        # Test first page
        response = client.get("/api/v1/media?page=1&page_size=10")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 10
        assert data["total"] == 15
        assert data["page"] == 1

        # Test second page
        response = client.get("/api/v1/media?page=2&page_size=10")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 5
        assert data["total"] == 15
        assert data["page"] == 2

    def test_media_filter_by_instance(self, authenticated_client, app) -> None:
        """Test filtering media by instance."""
        client = authenticated_client

        # Create two instances
        response = client.post(
            "/api/v1/instance",
            json={
                "name": "Sonarr",
                "type": "sonarr",
                "url": "http://localhost:8989",
                "api_key": "key1",
                "root_path": "/tv",
            },
        )
        sonarr_id = response.json()["id"]

        response = client.post(
            "/api/v1/instance",
            json={
                "name": "Radarr",
                "type": "radarr",
                "url": "http://localhost:7878",
                "api_key": "key2",
                "root_path": "/movies",
            },
        )
        radarr_id = response.json()["id"]

        # Add media to database
        from taggarr.db import get_session

        with get_session(app.state.db_engine) as db:
            # Add TV shows
            for i in range(3):
                media = Media(
                    instance_id=sonarr_id,
                    title=f"TV Show {i}",
                    clean_title=f"tv-show-{i}",
                    path=f"/tv/show-{i}",
                    media_type="series",
                    added=datetime.now(),
                )
                db.add(media)

            # Add movies
            for i in range(2):
                media = Media(
                    instance_id=radarr_id,
                    title=f"Movie {i}",
                    clean_title=f"movie-{i}",
                    path=f"/movies/movie-{i}",
                    media_type="movie",
                    added=datetime.now(),
                )
                db.add(media)
            db.commit()

        # Filter by Sonarr instance
        response = client.get(f"/api/v1/media?instance_id={sonarr_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        for item in data["items"]:
            assert item["instance_id"] == sonarr_id

        # Filter by Radarr instance
        response = client.get(f"/api/v1/media?instance_id={radarr_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        for item in data["items"]:
            assert item["instance_id"] == radarr_id

    def test_media_search(self, authenticated_client, app) -> None:
        """Test searching media by title."""
        client = authenticated_client

        # Create instance
        response = client.post(
            "/api/v1/instance",
            json={
                "name": "Test Sonarr",
                "type": "sonarr",
                "url": "http://localhost:8989",
                "api_key": "test-key",
                "root_path": "/tv",
            },
        )
        instance_id = response.json()["id"]

        # Add media
        from taggarr.db import get_session

        with get_session(app.state.db_engine) as db:
            shows = [
                ("Breaking Bad", "breaking-bad"),
                ("Better Call Saul", "better-call-saul"),
                ("The Wire", "the-wire"),
            ]
            for title, clean_title in shows:
                media = Media(
                    instance_id=instance_id,
                    title=title,
                    clean_title=clean_title,
                    path=f"/tv/{clean_title}",
                    media_type="series",
                    added=datetime.now(),
                )
                db.add(media)
            db.commit()

        # Search for "Breaking"
        response = client.get("/api/v1/media?search=Breaking")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["title"] == "Breaking Bad"

        # Search for "Better" (case-insensitive)
        response = client.get("/api/v1/media?search=better")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["title"] == "Better Call Saul"

    def test_get_media_detail(self, authenticated_client, app) -> None:
        """Test getting media details with seasons."""
        client = authenticated_client

        # Create instance
        response = client.post(
            "/api/v1/instance",
            json={
                "name": "Test Sonarr",
                "type": "sonarr",
                "url": "http://localhost:8989",
                "api_key": "test-key",
                "root_path": "/tv",
            },
        )
        instance_id = response.json()["id"]

        # Add media with seasons
        from taggarr.db import get_session

        with get_session(app.state.db_engine) as db:
            media = Media(
                instance_id=instance_id,
                title="Test Show",
                clean_title="test-show",
                path="/tv/test-show",
                media_type="series",
                original_language="en",
                added=datetime.now(),
            )
            db.add(media)
            db.flush()

            # Add seasons
            for season_num in [1, 2, 3]:
                season = Season(
                    media_id=media.id,
                    season_number=season_num,
                    episode_count=10,
                    status="dub",
                    original_dub=json.dumps(["en"]),
                    dub=json.dumps(["en", "es"]),
                )
                db.add(season)
            db.commit()

            media_id = media.id

        # Get media detail
        response = client.get(f"/api/v1/media/{media_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test Show"
        assert data["instance_name"] == "Test Sonarr"
        assert data["original_language"] == "en"
        assert len(data["seasons"]) == 3
        assert data["seasons"][0]["season_number"] == 1
        assert data["seasons"][0]["episode_count"] == 10

    def test_update_media_overrides(self, authenticated_client, app) -> None:
        """Test updating media override settings."""
        client = authenticated_client

        # Create instance
        response = client.post(
            "/api/v1/instance",
            json={
                "name": "Test Sonarr",
                "type": "sonarr",
                "url": "http://localhost:8989",
                "api_key": "test-key",
                "root_path": "/tv",
            },
        )
        instance_id = response.json()["id"]

        # Add media
        from taggarr.db import get_session

        with get_session(app.state.db_engine) as db:
            media = Media(
                instance_id=instance_id,
                title="Test Show",
                clean_title="test-show",
                path="/tv/test-show",
                media_type="series",
                added=datetime.now(),
            )
            db.add(media)
            db.commit()
            media_id = media.id

        # Update overrides
        response = client.put(
            f"/api/v1/media/{media_id}",
            json={
                "override_require_original": False,
                "override_notify": True,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["override_require_original"] is False
        assert data["override_notify"] is True

        # Clear overrides (set to None)
        response = client.put(
            f"/api/v1/media/{media_id}",
            json={
                "override_require_original": None,
                "override_notify": None,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["override_require_original"] is None
        assert data["override_notify"] is None

    def test_get_nonexistent_media(self, authenticated_client) -> None:
        """Test getting a nonexistent media returns 404."""
        response = authenticated_client.get("/api/v1/media/9999")
        assert response.status_code == 404
        assert response.json()["detail"] == "Media not found"
