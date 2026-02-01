"""Tests for taggarr.services.sonarr module."""

import logging
import pytest
import responses

from taggarr.services.sonarr import SonarrClient


@pytest.fixture
def client():
    """Create a SonarrClient for testing."""
    return SonarrClient(url="http://sonarr:8989", api_key="test-api-key")


class TestSonarrClientInit:
    """Tests for SonarrClient initialization."""

    def test_stores_url_without_trailing_slash(self):
        client = SonarrClient(url="http://sonarr:8989/", api_key="key")
        assert client.url == "http://sonarr:8989"

    def test_stores_api_key(self):
        client = SonarrClient(url="http://sonarr:8989", api_key="my-key")
        assert client.api_key == "my-key"

    def test_sets_headers_with_api_key(self):
        client = SonarrClient(url="http://sonarr:8989", api_key="my-key")
        assert client._headers == {"X-Api-Key": "my-key"}


class TestGetSeriesByPath:
    """Tests for get_series_by_path method."""

    @responses.activate
    def test_returns_series_when_found(self, client):
        responses.add(
            responses.GET,
            "http://sonarr:8989/api/v3/series",
            json=[
                {"id": 1, "title": "Breaking Bad", "path": "/media/tv/Breaking Bad"},
                {"id": 2, "title": "Better Call Saul", "path": "/media/tv/Better Call Saul"},
            ],
        )

        result = client.get_series_by_path("/media/tv/Breaking Bad")

        assert result is not None
        assert result["id"] == 1
        assert result["title"] == "Breaking Bad"

    @responses.activate
    def test_returns_none_when_not_found(self, client):
        responses.add(
            responses.GET,
            "http://sonarr:8989/api/v3/series",
            json=[{"id": 1, "title": "Breaking Bad", "path": "/media/tv/Breaking Bad"}],
        )

        result = client.get_series_by_path("/media/tv/Nonexistent Show")

        assert result is None

    @responses.activate
    def test_returns_none_on_api_error(self, client):
        responses.add(
            responses.GET,
            "http://sonarr:8989/api/v3/series",
            status=500,
        )

        result = client.get_series_by_path("/media/tv/Breaking Bad")

        assert result is None

    @responses.activate
    def test_matches_by_basename(self, client):
        """Test that matching is done by folder basename, not full path."""
        responses.add(
            responses.GET,
            "http://sonarr:8989/api/v3/series",
            json=[
                {"id": 1, "title": "Show", "path": "/different/root/Show"},
            ],
        )

        result = client.get_series_by_path("/media/tv/Show")

        assert result is not None
        assert result["id"] == 1


class TestGetSeriesId:
    """Tests for get_series_id method."""

    @responses.activate
    def test_returns_id_when_found(self, client):
        responses.add(
            responses.GET,
            "http://sonarr:8989/api/v3/series",
            json=[{"id": 42, "title": "Test", "path": "/media/tv/Test"}],
        )

        result = client.get_series_id("/media/tv/Test")

        assert result == 42

    @responses.activate
    def test_returns_none_when_not_found(self, client):
        responses.add(
            responses.GET,
            "http://sonarr:8989/api/v3/series",
            json=[],
        )

        result = client.get_series_id("/media/tv/Nonexistent")

        assert result is None


class TestAddTag:
    """Tests for add_tag method."""

    @responses.activate
    def test_adds_tag_to_series(self, client):
        # Mock get tags (tag doesn't exist)
        responses.add(
            responses.GET,
            "http://sonarr:8989/api/v3/tag",
            json=[],
        )
        # Mock create tag
        responses.add(
            responses.POST,
            "http://sonarr:8989/api/v3/tag",
            json={"id": 1, "label": "dub"},
        )
        # Mock get series
        responses.add(
            responses.GET,
            "http://sonarr:8989/api/v3/series/42",
            json={"id": 42, "title": "Test", "tags": []},
        )
        # Mock update series
        responses.add(
            responses.PUT,
            "http://sonarr:8989/api/v3/series/42",
            json={"id": 42, "title": "Test", "tags": [1]},
        )

        client.add_tag(42, "dub")

        # Verify PUT was called
        put_calls = [c for c in responses.calls if c.request.method == "PUT"]
        assert len(put_calls) == 1

    def test_dry_run_does_not_call_api(self, client, caplog):
        # No responses mocked - would fail if API called
        caplog.set_level(logging.INFO)
        client.add_tag(42, "dub", dry_run=True)

        assert "Dry Run" in caplog.text

    @responses.activate
    def test_uses_existing_tag_if_found(self, client):
        # Mock get tags (tag exists)
        responses.add(
            responses.GET,
            "http://sonarr:8989/api/v3/tag",
            json=[{"id": 5, "label": "dub"}],
        )
        # Mock get series
        responses.add(
            responses.GET,
            "http://sonarr:8989/api/v3/series/42",
            json={"id": 42, "title": "Test", "tags": []},
        )
        # Mock update series
        responses.add(
            responses.PUT,
            "http://sonarr:8989/api/v3/series/42",
            json={"id": 42, "title": "Test", "tags": [5]},
        )

        client.add_tag(42, "dub")

        # Should not have created a new tag
        assert len([c for c in responses.calls if c.request.method == "POST"]) == 0

    @responses.activate
    def test_does_not_add_duplicate_tag(self, client):
        """Test that tag is not added if series already has it."""
        responses.add(
            responses.GET,
            "http://sonarr:8989/api/v3/tag",
            json=[{"id": 5, "label": "dub"}],
        )
        responses.add(
            responses.GET,
            "http://sonarr:8989/api/v3/series/42",
            json={"id": 42, "title": "Test", "tags": [5]},  # Already has tag
        )
        responses.add(
            responses.PUT,
            "http://sonarr:8989/api/v3/series/42",
            json={"id": 42, "title": "Test", "tags": [5]},
        )

        client.add_tag(42, "dub")

        # PUT should still be called but tag list unchanged
        put_calls = [c for c in responses.calls if c.request.method == "PUT"]
        assert len(put_calls) == 1


class TestRemoveTag:
    """Tests for remove_tag method."""

    @responses.activate
    def test_removes_tag_from_series(self, client):
        # Mock get tags
        responses.add(
            responses.GET,
            "http://sonarr:8989/api/v3/tag",
            json=[{"id": 5, "label": "dub"}],
        )
        # Mock get series (has the tag)
        responses.add(
            responses.GET,
            "http://sonarr:8989/api/v3/series/42",
            json={"id": 42, "title": "Test", "tags": [5]},
        )
        # Mock update series
        responses.add(
            responses.PUT,
            "http://sonarr:8989/api/v3/series/42",
            json={"id": 42, "title": "Test", "tags": []},
        )

        client.remove_tag(42, "dub")

        # Verify PUT was called
        put_calls = [c for c in responses.calls if c.request.method == "PUT"]
        assert len(put_calls) == 1

    @responses.activate
    def test_does_nothing_if_tag_not_found(self, client):
        # Mock get tags (tag doesn't exist)
        responses.add(
            responses.GET,
            "http://sonarr:8989/api/v3/tag",
            json=[],
        )

        # Should not throw
        client.remove_tag(42, "nonexistent")

    def test_dry_run_does_not_call_api(self, client, caplog):
        caplog.set_level(logging.INFO)
        client.remove_tag(42, "dub", dry_run=True)
        assert "Dry Run" in caplog.text


class TestRefreshSeries:
    """Tests for refresh_series method."""

    @responses.activate
    def test_triggers_refresh_command(self, client):
        responses.add(
            responses.POST,
            "http://sonarr:8989/api/v3/command",
            json={"id": 1},
        )

        client.refresh_series(42)

        post_call = responses.calls[0]
        assert "RefreshSeries" in post_call.request.body.decode()
        assert "42" in post_call.request.body.decode()

    def test_dry_run_does_not_call_api(self, client, caplog):
        caplog.set_level(logging.INFO)
        client.refresh_series(42, dry_run=True)
        assert "Dry Run" in caplog.text

    @responses.activate
    def test_handles_connection_error(self, client, caplog):
        caplog.set_level(logging.WARNING)
        responses.add(
            responses.POST,
            "http://sonarr:8989/api/v3/command",
            body=Exception("Connection refused"),
        )

        # Should not raise
        client.refresh_series(42)

        assert "Failed to trigger" in caplog.text


class TestGetTagId:
    """Tests for _get_tag_id method."""

    @responses.activate
    def test_returns_id_for_existing_tag(self, client):
        responses.add(
            responses.GET,
            "http://sonarr:8989/api/v3/tag",
            json=[
                {"id": 1, "label": "dub"},
                {"id": 2, "label": "semi-dub"},
            ],
        )

        result = client._get_tag_id("dub")

        assert result == 1

    @responses.activate
    def test_returns_none_for_nonexistent_tag(self, client):
        responses.add(
            responses.GET,
            "http://sonarr:8989/api/v3/tag",
            json=[{"id": 1, "label": "other"}],
        )

        result = client._get_tag_id("dub")

        assert result is None

    @responses.activate
    def test_case_insensitive_matching(self, client):
        responses.add(
            responses.GET,
            "http://sonarr:8989/api/v3/tag",
            json=[{"id": 1, "label": "DUB"}],
        )

        result = client._get_tag_id("dub")

        assert result == 1

    @responses.activate
    def test_returns_none_on_api_error(self, client):
        responses.add(
            responses.GET,
            "http://sonarr:8989/api/v3/tag",
            status=500,
        )

        result = client._get_tag_id("dub")

        assert result is None


class TestModifySeriesTags:
    """Tests for _modify_series_tags method."""

    @responses.activate
    def test_handles_api_error(self, client, caplog):
        caplog.set_level(logging.WARNING)
        responses.add(
            responses.GET,
            "http://sonarr:8989/api/v3/series/42",
            status=500,
        )

        # Should not raise
        client._modify_series_tags(42, 1, remove=False)

        assert "Failed to modify" in caplog.text

    @responses.activate
    def test_removes_tag_when_present(self, client):
        responses.add(
            responses.GET,
            "http://sonarr:8989/api/v3/series/42",
            json={"id": 42, "tags": [1, 2, 3]},
        )
        responses.add(
            responses.PUT,
            "http://sonarr:8989/api/v3/series/42",
            json={"id": 42, "tags": [1, 3]},
        )

        client._modify_series_tags(42, 2, remove=True)

        put_calls = [c for c in responses.calls if c.request.method == "PUT"]
        assert len(put_calls) == 1
