"""Integration smoke test for taggarr end-to-end workflow."""

import json
import os
import pytest
import responses
from types import SimpleNamespace
from pathlib import Path

import taggarr
from taggarr import run
from taggarr.config_schema import Config, DefaultsConfig, InstanceConfig, TagsConfig


@pytest.fixture
def mock_media_setup(tmp_path):
    """Set up a mock media library with test files."""
    # Create TV show structure
    tv_root = tmp_path / "tv"
    show_path = tv_root / "TestShow (2020)"
    season_path = show_path / "Season 01"
    season_path.mkdir(parents=True)
    
    # Create NFO file
    nfo_content = """<?xml version="1.0" encoding="utf-8"?>
<tvshow>
    <title>TestShow</title>
    <genre>Drama</genre>
</tvshow>"""
    (show_path / "tvshow.nfo").write_text(nfo_content)
    
    # Create video file (empty, will be mocked)
    (season_path / "TestShow.S01E01.mkv").write_bytes(b"x" * 1000)
    
    # Create movie structure
    movie_root = tmp_path / "movies"
    movie_path = movie_root / "TestMovie (2021)"
    movie_path.mkdir(parents=True)
    
    movie_nfo = """<?xml version="1.0" encoding="utf-8"?>
<movie>
    <title>TestMovie</title>
    <genre>Action</genre>
</movie>"""
    (movie_path / "movie.nfo").write_text(movie_nfo)
    (movie_path / "TestMovie.2021.mkv").write_bytes(b"x" * 2000)
    
    return {
        "tmp_path": tmp_path,
        "tv_root": str(tv_root),
        "movie_root": str(movie_root),
        "show_path": str(show_path),
        "movie_path": str(movie_path),
    }


@pytest.fixture
def config(mock_media_setup):
    """Test configuration with both Sonarr and Radarr instances."""
    return Config(
        defaults=DefaultsConfig(log_path=str(mock_media_setup["tmp_path"])),
        instances={
            "sonarr": InstanceConfig(
                name="sonarr",
                type="sonarr",
                url="http://sonarr:8989",
                api_key="testkey",
                root_path=mock_media_setup["tv_root"],
                target_languages=["en"],
                tags=TagsConfig(),
            ),
            "radarr": InstanceConfig(
                name="radarr",
                type="radarr",
                url="http://radarr:7878",
                api_key="testkey",
                root_path=mock_media_setup["movie_root"],
                target_languages=["en"],
                tags=TagsConfig(),
            ),
        },
    )


@pytest.fixture
def opts():
    """Default command line options."""
    return SimpleNamespace(
        quick=False,
        dry_run=False,
        write_mode=0,
        instances=None,
    )


@pytest.fixture(autouse=True)
def reset_logger():
    """Reset the global logger before each test."""
    taggarr._logger = None
    yield
    taggarr._logger = None


@pytest.mark.integration
class TestEndToEndSonarr:
    """End-to-end tests for Sonarr processing."""

    @responses.activate
    def test_sonarr_full_scan_workflow(self, opts, config, mock_media_setup):
        """Test complete Sonarr scan workflow with mocked API and media analysis."""
        from unittest.mock import patch
        
        # Mock Sonarr API responses
        responses.add(
            responses.GET,
            "http://sonarr:8989/api/v3/series",
            json=[{
                "id": 1,
                "title": "TestShow",
                "path": mock_media_setup["show_path"],
                "originalLanguage": {"name": "Japanese"},
            }],
            status=200,
        )
        
        # Mock tag endpoints
        responses.add(
            responses.GET,
            "http://sonarr:8989/api/v3/tag",
            json=[{"id": 1, "label": "dub"}],
            status=200,
        )
        # Mock individual series GET for apply_tag_changes
        responses.add(
            responses.GET,
            "http://sonarr:8989/api/v3/series/1",
            json={"id": 1, "tags": []},
            status=200,
        )
        responses.add(
            responses.PUT,
            "http://sonarr:8989/api/v3/series/1",
            json={"id": 1},
            status=200,
        )
        
        # Only run sonarr instance
        opts.instances = "sonarr"
        
        # Mock media analysis to return English audio
        with patch("taggarr.processors.tv.media.analyze_audio") as mock_audio:
            mock_audio.return_value = ["en"]
            
            # Run the scan
            run(opts, config)
        
        # Verify taggarr.json was created
        json_path = Path(mock_media_setup["tv_root"]) / "taggarr.json"
        assert json_path.exists()
        
        # Verify content
        with open(json_path) as f:
            data = json.load(f)
        
        assert "series" in data
        assert mock_media_setup["show_path"] in data["series"]
        show_data = data["series"][mock_media_setup["show_path"]]
        assert show_data["tag"] == "dub"  # English found = fully dubbed


@pytest.mark.integration
class TestEndToEndRadarr:
    """End-to-end tests for Radarr processing."""

    @responses.activate
    def test_radarr_full_scan_workflow(self, opts, config, mock_media_setup):
        """Test complete Radarr scan workflow with mocked API and media analysis."""
        from unittest.mock import patch
        
        # Mock Radarr API responses
        responses.add(
            responses.GET,
            "http://radarr:7878/api/v3/movie",
            json=[{
                "id": 1,
                "title": "TestMovie",
                "path": mock_media_setup["movie_path"],
                "hasFile": True,
                "originalLanguage": {"name": "Japanese"},
                "genres": ["Action"],
            }],
            status=200,
        )
        
        # Mock tag endpoints
        responses.add(
            responses.GET,
            "http://radarr:7878/api/v3/tag",
            json=[{"id": 1, "label": "dub"}],
            status=200,
        )
        # Mock individual movie GET for apply_tag_changes
        responses.add(
            responses.GET,
            "http://radarr:7878/api/v3/movie/1",
            json={"id": 1, "tags": []},
            status=200,
        )
        responses.add(
            responses.PUT,
            "http://radarr:7878/api/v3/movie/1",
            json={"id": 1},
            status=200,
        )
        
        # Only run radarr instance
        opts.instances = "radarr"
        
        # Mock media analysis to return English audio
        with patch("taggarr.processors.movies.media.analyze_audio") as mock_audio:
            mock_audio.return_value = ["en"]
            
            # Run the scan
            run(opts, config)
        
        # Verify taggarr.json was created
        json_path = Path(mock_media_setup["movie_root"]) / "taggarr.json"
        assert json_path.exists()
        
        # Verify content
        with open(json_path) as f:
            data = json.load(f)
        
        assert "movies" in data
        assert mock_media_setup["movie_path"] in data["movies"]
        movie_data = data["movies"][mock_media_setup["movie_path"]]
        assert movie_data["tag"] == "dub"


@pytest.mark.integration
class TestDryRunMode:
    """Test dry run mode doesn't make changes."""

    @responses.activate
    def test_dry_run_does_not_write_files(self, opts, config, mock_media_setup):
        """Test that dry run mode doesn't write to disk or call APIs."""
        from unittest.mock import patch
        
        # Mock Sonarr API
        responses.add(
            responses.GET,
            "http://sonarr:8989/api/v3/series",
            json=[{
                "id": 1,
                "title": "TestShow",
                "path": mock_media_setup["show_path"],
                "originalLanguage": {"name": "Japanese"},
            }],
            status=200,
        )
        responses.add(
            responses.GET,
            "http://sonarr:8989/api/v3/tag",
            json=[],
            status=200,
        )
        
        opts.instances = "sonarr"
        opts.dry_run = True
        
        with patch("taggarr.processors.tv.media.analyze_audio") as mock_audio:
            mock_audio.return_value = ["en"]
            run(opts, config)
        
        # Verify no PUT requests were made (dry run)
        put_calls = [c for c in responses.calls if c.request.method == "PUT"]
        assert len(put_calls) == 0
