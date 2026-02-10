"""Shared test fixtures for taggarr tests."""

import pytest
from unittest.mock import Mock
from taggarr.config_schema import (
    Config, DefaultsConfig, InstanceConfig, TagsConfig
)


@pytest.fixture(autouse=True)
def _fast_retries(monkeypatch):
    """Disable tenacity wait times in all tests."""
    monkeypatch.setattr("tenacity.nap.time.sleep", lambda x: None)


@pytest.fixture
def tags_config():
    """Default tags configuration."""
    return TagsConfig(dub="dub", semi="semi-dub", wrong="wrong-dub")


@pytest.fixture
def defaults_config(tags_config):
    """Default configuration."""
    return DefaultsConfig(
        target_languages=["en"],
        tags=tags_config,
        dry_run=False,
        quick_mode=False,
        run_interval_seconds=7200,
        log_level="INFO",
        log_path="/tmp/taggarr-tests",
    )


@pytest.fixture
def sonarr_instance(tags_config):
    """Sample Sonarr instance configuration."""
    return InstanceConfig(
        name="sonarr-test",
        type="sonarr",
        url="http://sonarr:8989",
        api_key="test-api-key",
        root_path="/media/tv",
        target_languages=["en"],
        tags=tags_config,
        dry_run=False,
        quick_mode=False,
        target_genre=None,
    )


@pytest.fixture
def radarr_instance(tags_config):
    """Sample Radarr instance configuration."""
    return InstanceConfig(
        name="radarr-test",
        type="radarr",
        url="http://radarr:7878",
        api_key="test-api-key",
        root_path="/media/movies",
        target_languages=["en"],
        tags=tags_config,
        dry_run=False,
        quick_mode=False,
        target_genre=None,
    )


@pytest.fixture
def config(defaults_config, sonarr_instance):
    """Complete configuration with one Sonarr instance."""
    return Config(
        defaults=defaults_config,
        instances={"sonarr-test": sonarr_instance},
    )


@pytest.fixture
def mock_sonarr_client(mocker):
    """Mocked SonarrClient."""
    from taggarr.services.sonarr import SonarrClient
    return mocker.Mock(spec=SonarrClient)


@pytest.fixture
def mock_radarr_client(mocker):
    """Mocked RadarrClient."""
    from taggarr.services.radarr import RadarrClient
    return mocker.Mock(spec=RadarrClient)


@pytest.fixture
def sample_series():
    """Sample Sonarr series data."""
    return {
        "id": 1,
        "title": "Breaking Bad",
        "path": "/media/tv/Breaking Bad",
        "originalLanguage": {"name": "English"},
        "tags": [],
    }


@pytest.fixture
def sample_movie():
    """Sample Radarr movie data."""
    return {
        "id": 1,
        "title": "Inception",
        "path": "/media/movies/Inception (2010)",
        "originalLanguage": {"name": "English"},
        "hasFile": True,
        "genres": ["Action", "Sci-Fi"],
        "tags": [],
    }
