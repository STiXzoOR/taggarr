"""Tests for taggarr.services.sonarr module."""

import logging
import pytest
import requests
import responses

from taggarr.services.sonarr import SonarrClient
from taggarr.exceptions import ApiTransientError, ApiPermanentError


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
    def test_matches_by_full_path_first(self, client):
        """Test that full path matching takes priority over basename."""
        responses.add(
            responses.GET,
            "http://sonarr:8989/api/v3/series",
            json=[
                {"id": 1, "title": "Show A", "path": "/other/root/Show"},
                {"id": 2, "title": "Show B", "path": "/media/tv/Show"},
            ],
        )

        result = client.get_series_by_path("/media/tv/Show")

        assert result is not None
        assert result["id"] == 2

    @responses.activate
    def test_falls_back_to_basename(self, client):
        """Test basename fallback when full path doesn't match."""
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

    @responses.activate
    def test_uses_cache_on_second_call(self, client):
        """Test that media list is cached across calls."""
        responses.add(
            responses.GET,
            "http://sonarr:8989/api/v3/series",
            json=[{"id": 1, "title": "Test", "path": "/media/tv/Test"}],
        )

        client.get_series_by_path("/media/tv/Test")
        client.get_series_by_path("/media/tv/Test")

        # Only one API call should be made
        assert len(responses.calls) == 1


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
    def test_does_not_modify_when_tag_already_present(self, client):
        """Test that no PUT is made if series already has the tag."""
        responses.add(
            responses.GET,
            "http://sonarr:8989/api/v3/tag",
            json=[{"id": 5, "label": "dub"}],
        )
        responses.add(
            responses.GET,
            "http://sonarr:8989/api/v3/series/42",
            json={"id": 42, "title": "Test", "tags": [5]},
        )

        client.add_tag(42, "dub")

        # No PUT should be made since tag already exists
        put_calls = [c for c in responses.calls if c.request.method == "PUT"]
        assert len(put_calls) == 0


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

        # Should not throw - and should not try to GET/PUT the series
        client.remove_tag(42, "nonexistent")

        # Only the tag lookup should happen
        assert len(responses.calls) == 1

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
            body=requests.ConnectionError("Connection refused"),
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


class TestApplyTagChanges:
    """Tests for apply_tag_changes method (atomic tag operations)."""

    @responses.activate
    def test_adds_and_removes_in_single_put(self, client):
        """Verify atomic: one GET + one PUT regardless of tag count."""
        responses.add(
            responses.GET,
            "http://sonarr:8989/api/v3/tag",
            json=[{"id": 1, "label": "dub"}, {"id": 2, "label": "semi-dub"}, {"id": 3, "label": "wrong-dub"}],
        )
        responses.add(
            responses.GET,
            "http://sonarr:8989/api/v3/series/42",
            json={"id": 42, "tags": [2]},
        )
        responses.add(
            responses.PUT,
            "http://sonarr:8989/api/v3/series/42",
            json={"id": 42, "tags": [1]},
        )

        client.apply_tag_changes(42, add_tags=["dub"], remove_tags=["semi-dub", "wrong-dub"])

        put_calls = [c for c in responses.calls if c.request.method == "PUT"]
        assert len(put_calls) == 1

    @responses.activate
    def test_skips_put_when_no_changes(self, client):
        """No PUT if resulting tags are the same."""
        responses.add(
            responses.GET,
            "http://sonarr:8989/api/v3/tag",
            json=[{"id": 1, "label": "dub"}],
        )
        responses.add(
            responses.GET,
            "http://sonarr:8989/api/v3/series/42",
            json={"id": 42, "tags": [1]},
        )

        client.apply_tag_changes(42, add_tags=["dub"], remove_tags=["nonexistent"])

        put_calls = [c for c in responses.calls if c.request.method == "PUT"]
        assert len(put_calls) == 0

    @responses.activate
    def test_handles_api_error_on_get(self, client, caplog):
        """API errors during GET propagate."""
        caplog.set_level(logging.WARNING)
        responses.add(
            responses.GET,
            "http://sonarr:8989/api/v3/tag",
            json=[{"id": 1, "label": "dub"}],
        )
        responses.add(
            responses.GET,
            "http://sonarr:8989/api/v3/series/42",
            status=500,
        )

        with pytest.raises(ApiTransientError):
            client.apply_tag_changes(42, add_tags=["dub"])

    def test_returns_early_when_no_tags(self, client):
        """No API calls when both add_tags and remove_tags are empty."""
        client.apply_tag_changes(42, add_tags=[], remove_tags=[])
        # No responses mocked - would fail if any API call was made

    def test_dry_run_logs_add_and_remove(self, client, caplog):
        """Dry run logs both add and remove operations."""
        caplog.set_level(logging.INFO)
        client.apply_tag_changes(42, add_tags=["dub"], remove_tags=["wrong-dub"], dry_run=True)
        assert "Dry Run" in caplog.text
        assert "add" in caplog.text.lower()
        assert "remove" in caplog.text.lower()

    @responses.activate
    def test_creates_tag_if_not_exists(self, client):
        """Tag is created via POST when it doesn't exist."""
        responses.add(
            responses.GET,
            "http://sonarr:8989/api/v3/tag",
            json=[],
        )
        responses.add(
            responses.POST,
            "http://sonarr:8989/api/v3/tag",
            json={"id": 10, "label": "new-tag"},
        )
        responses.add(
            responses.GET,
            "http://sonarr:8989/api/v3/series/42",
            json={"id": 42, "tags": []},
        )
        responses.add(
            responses.PUT,
            "http://sonarr:8989/api/v3/series/42",
            json={"id": 42, "tags": [10]},
        )

        client.apply_tag_changes(42, add_tags=["new-tag"])

        post_calls = [c for c in responses.calls if c.request.method == "POST"]
        assert len(post_calls) == 1


class TestBaseClientRequest:
    """Tests for BaseArrClient._request error handling."""

    @responses.activate
    def test_timeout_raises_transient_error(self, client):
        """Timeout should raise ApiTransientError."""
        responses.add(
            responses.GET,
            "http://sonarr:8989/api/v3/series",
            body=requests.Timeout("timed out"),
        )

        with pytest.raises(ApiTransientError, match="timed out"):
            client._request("GET", "/api/v3/series")

    @responses.activate
    def test_4xx_raises_permanent_error(self, client):
        """4xx HTTP errors should raise ApiPermanentError."""
        responses.add(
            responses.GET,
            "http://sonarr:8989/api/v3/series",
            status=404,
        )

        with pytest.raises(ApiPermanentError, match="client error"):
            client._request("GET", "/api/v3/series")

    @responses.activate
    def test_retries_on_transient_error_then_succeeds(self, client):
        """Transient errors are retried and succeed on subsequent attempt."""
        # First call: 500 error (transient)
        responses.add(
            responses.GET,
            "http://sonarr:8989/api/v3/series",
            status=500,
        )
        # Second call: success
        responses.add(
            responses.GET,
            "http://sonarr:8989/api/v3/series",
            json=[{"id": 1}],
            status=200,
        )

        result = client._request("GET", "/api/v3/series")

        assert result.json() == [{"id": 1}]
        assert len(responses.calls) == 2

    @responses.activate
    def test_does_not_retry_permanent_errors(self, client):
        """Permanent errors (4xx) are not retried."""
        responses.add(
            responses.GET,
            "http://sonarr:8989/api/v3/series",
            status=404,
        )

        with pytest.raises(ApiPermanentError):
            client._request("GET", "/api/v3/series")

        assert len(responses.calls) == 1

    @responses.activate
    def test_tag_creation_failure_raises_permanent_error(self, client):
        """Failed tag creation should raise ApiPermanentError."""
        responses.add(
            responses.GET,
            "http://sonarr:8989/api/v3/tag",
            json=[],
        )
        responses.add(
            responses.POST,
            "http://sonarr:8989/api/v3/tag",
            status=500,
        )

        with pytest.raises(ApiPermanentError, match="Failed to create tag"):
            client._get_or_create_tag("new-tag")


class TestClearCache:
    """Tests for clear_cache method."""

    def test_clears_both_caches(self, client):
        """clear_cache should reset media and tag caches."""
        client._media_cache = [{"id": 1}]
        client._tag_cache = [{"id": 1, "label": "dub"}]

        client.clear_cache()

        assert client._media_cache is None
        assert client._tag_cache is None
