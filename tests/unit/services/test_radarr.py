"""Tests for taggarr.services.radarr module."""

import logging
import pytest
import responses

from taggarr.services.radarr import RadarrClient


@pytest.fixture
def client():
    """Create a RadarrClient for testing."""
    return RadarrClient(url="http://radarr:7878", api_key="test-api-key")


class TestRadarrClientInit:
    """Tests for RadarrClient initialization."""

    def test_stores_url_without_trailing_slash(self):
        client = RadarrClient(url="http://radarr:7878/", api_key="key")
        assert client.url == "http://radarr:7878"

    def test_stores_api_key(self):
        client = RadarrClient(url="http://radarr:7878", api_key="my-key")
        assert client.api_key == "my-key"

    def test_sets_headers_with_api_key(self):
        client = RadarrClient(url="http://radarr:7878", api_key="my-key")
        assert client._headers == {"X-Api-Key": "my-key"}


class TestGetMovies:
    """Tests for get_movies method."""

    @responses.activate
    def test_returns_all_movies(self, client):
        responses.add(
            responses.GET,
            "http://radarr:7878/api/v3/movie",
            json=[
                {"id": 1, "title": "Inception"},
                {"id": 2, "title": "Interstellar"},
            ],
        )

        result = client.get_movies()

        assert len(result) == 2
        assert result[0]["title"] == "Inception"

    @responses.activate
    def test_returns_empty_list_on_error(self, client, caplog):
        caplog.set_level(logging.WARNING)
        responses.add(
            responses.GET,
            "http://radarr:7878/api/v3/movie",
            body=Exception("Connection error"),
        )

        result = client.get_movies()

        assert result == []
        assert "Failed to fetch" in caplog.text


class TestGetMovieByPath:
    """Tests for get_movie_by_path method."""

    @responses.activate
    def test_returns_movie_when_found(self, client):
        responses.add(
            responses.GET,
            "http://radarr:7878/api/v3/movie",
            json=[
                {"id": 1, "title": "Inception", "path": "/media/movies/Inception (2010)"},
            ],
        )

        result = client.get_movie_by_path("/media/movies/Inception (2010)")

        assert result is not None
        assert result["id"] == 1

    @responses.activate
    def test_returns_none_when_not_found_empty_list(self, client):
        responses.add(
            responses.GET,
            "http://radarr:7878/api/v3/movie",
            json=[],
        )

        result = client.get_movie_by_path("/nonexistent")

        assert result is None

    @responses.activate
    def test_returns_none_when_no_path_match(self, client):
        """Test when movies exist but none match the path."""
        responses.add(
            responses.GET,
            "http://radarr:7878/api/v3/movie",
            json=[
                {"id": 1, "title": "Other Movie", "path": "/media/movies/Other Movie (2020)"},
            ],
        )

        result = client.get_movie_by_path("/media/movies/Nonexistent (2020)")

        assert result is None

    @responses.activate
    def test_returns_none_on_api_error(self, client, caplog):
        caplog.set_level(logging.WARNING)
        responses.add(
            responses.GET,
            "http://radarr:7878/api/v3/movie",
            body=Exception("Connection error"),
        )

        result = client.get_movie_by_path("/media/movies/Test")

        assert result is None
        assert "Radarr lookup failed" in caplog.text

    @responses.activate
    def test_matches_by_basename(self, client):
        """Test that matching is done by folder basename, not full path."""
        responses.add(
            responses.GET,
            "http://radarr:7878/api/v3/movie",
            json=[
                {"id": 1, "title": "Movie", "path": "/different/root/Movie (2020)"},
            ],
        )

        result = client.get_movie_by_path("/media/movies/Movie (2020)")

        assert result is not None
        assert result["id"] == 1


class TestAddTag:
    """Tests for add_tag method."""

    @responses.activate
    def test_adds_tag_to_movie(self, client):
        responses.add(responses.GET, "http://radarr:7878/api/v3/tag", json=[])
        responses.add(responses.POST, "http://radarr:7878/api/v3/tag", json={"id": 1, "label": "dub"})
        responses.add(responses.GET, "http://radarr:7878/api/v3/movie/42", json={"id": 42, "tags": []})
        responses.add(responses.PUT, "http://radarr:7878/api/v3/movie/42", json={"id": 42, "tags": [1]})

        client.add_tag(42, "dub")

        assert len([c for c in responses.calls if c.request.method == "PUT"]) == 1

    def test_dry_run_does_not_call_api(self, client, caplog):
        caplog.set_level(logging.INFO)
        client.add_tag(42, "dub", dry_run=True)
        assert "Dry Run" in caplog.text

    @responses.activate
    def test_uses_existing_tag_if_found(self, client):
        responses.add(responses.GET, "http://radarr:7878/api/v3/tag", json=[{"id": 5, "label": "dub"}])
        responses.add(responses.GET, "http://radarr:7878/api/v3/movie/42", json={"id": 42, "tags": []})
        responses.add(responses.PUT, "http://radarr:7878/api/v3/movie/42", json={"id": 42, "tags": [5]})

        client.add_tag(42, "dub")

        # Should not have created a new tag
        assert len([c for c in responses.calls if c.request.method == "POST"]) == 0

    @responses.activate
    def test_does_not_add_duplicate_tag(self, client):
        """Test that tag is not added if movie already has it."""
        responses.add(responses.GET, "http://radarr:7878/api/v3/tag", json=[{"id": 5, "label": "dub"}])
        responses.add(responses.GET, "http://radarr:7878/api/v3/movie/42", json={"id": 42, "tags": [5]})
        responses.add(responses.PUT, "http://radarr:7878/api/v3/movie/42", json={"id": 42, "tags": [5]})

        client.add_tag(42, "dub")

        # PUT should still be called but tag list unchanged
        put_calls = [c for c in responses.calls if c.request.method == "PUT"]
        assert len(put_calls) == 1


class TestRemoveTag:
    """Tests for remove_tag method."""

    @responses.activate
    def test_removes_tag_from_movie(self, client):
        responses.add(responses.GET, "http://radarr:7878/api/v3/tag", json=[{"id": 5, "label": "dub"}])
        responses.add(responses.GET, "http://radarr:7878/api/v3/movie/42", json={"id": 42, "tags": [5]})
        responses.add(responses.PUT, "http://radarr:7878/api/v3/movie/42", json={"id": 42, "tags": []})

        client.remove_tag(42, "dub")

        assert len([c for c in responses.calls if c.request.method == "PUT"]) == 1

    @responses.activate
    def test_does_nothing_if_tag_not_found(self, client):
        responses.add(responses.GET, "http://radarr:7878/api/v3/tag", json=[])

        client.remove_tag(42, "nonexistent")  # Should not raise

    def test_dry_run_does_not_call_api(self, client, caplog):
        caplog.set_level(logging.INFO)
        client.remove_tag(42, "dub", dry_run=True)
        assert "Dry Run" in caplog.text


class TestGetTagId:
    """Tests for _get_tag_id method."""

    @responses.activate
    def test_returns_id_for_existing_tag(self, client):
        responses.add(
            responses.GET,
            "http://radarr:7878/api/v3/tag",
            json=[{"id": 3, "label": "dub"}],
        )

        result = client._get_tag_id("dub")

        assert result == 3

    @responses.activate
    def test_returns_none_for_nonexistent_tag(self, client):
        responses.add(
            responses.GET,
            "http://radarr:7878/api/v3/tag",
            json=[{"id": 1, "label": "other"}],
        )

        result = client._get_tag_id("dub")

        assert result is None

    @responses.activate
    def test_case_insensitive_matching(self, client):
        responses.add(
            responses.GET,
            "http://radarr:7878/api/v3/tag",
            json=[{"id": 3, "label": "DUB"}],
        )

        result = client._get_tag_id("dub")

        assert result == 3

    @responses.activate
    def test_returns_none_on_api_error(self, client):
        responses.add(
            responses.GET,
            "http://radarr:7878/api/v3/tag",
            body=Exception("Connection error"),
        )

        result = client._get_tag_id("dub")

        assert result is None


class TestModifyMovieTags:
    """Tests for _modify_movie_tags method."""

    @responses.activate
    def test_handles_api_error(self, client, caplog):
        caplog.set_level(logging.WARNING)
        responses.add(
            responses.GET,
            "http://radarr:7878/api/v3/movie/42",
            body=Exception("Connection error"),
        )

        # Should not raise
        client._modify_movie_tags(42, 1, remove=False)

        assert "Failed to modify" in caplog.text

    @responses.activate
    def test_removes_tag_when_present(self, client):
        responses.add(
            responses.GET,
            "http://radarr:7878/api/v3/movie/42",
            json={"id": 42, "tags": [1, 2, 3]},
        )
        responses.add(
            responses.PUT,
            "http://radarr:7878/api/v3/movie/42",
            json={"id": 42, "tags": [1, 3]},
        )

        client._modify_movie_tags(42, 2, remove=True)

        put_calls = [c for c in responses.calls if c.request.method == "PUT"]
        assert len(put_calls) == 1
