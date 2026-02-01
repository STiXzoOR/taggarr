"""Tests for taggarr.config_schema module."""

import pytest
from taggarr.config_schema import (
    TagsConfig, DefaultsConfig, InstanceConfig, Config
)


class TestTagsConfig:
    """Tests for TagsConfig dataclass."""

    def test_default_values(self):
        tags = TagsConfig()
        assert tags.dub == "dub"
        assert tags.semi == "semi-dub"
        assert tags.wrong == "wrong-dub"

    def test_custom_values(self):
        tags = TagsConfig(dub="dubbed", semi="partial", wrong="unexpected")
        assert tags.dub == "dubbed"
        assert tags.semi == "partial"
        assert tags.wrong == "unexpected"


class TestDefaultsConfig:
    """Tests for DefaultsConfig dataclass."""

    def test_default_values(self):
        defaults = DefaultsConfig()
        assert defaults.target_languages == ["en"]
        assert defaults.dry_run is False
        assert defaults.quick_mode is False
        assert defaults.run_interval_seconds == 7200
        assert defaults.log_level == "INFO"
        assert defaults.log_path == "/logs"

    def test_tags_default_is_tags_config(self):
        defaults = DefaultsConfig()
        assert isinstance(defaults.tags, TagsConfig)
        assert defaults.tags.dub == "dub"

    def test_custom_values(self):
        defaults = DefaultsConfig(
            target_languages=["ja", "en"],
            dry_run=True,
            quick_mode=True,
            run_interval_seconds=3600,
            log_level="DEBUG",
            log_path="/custom/logs",
        )
        assert defaults.target_languages == ["ja", "en"]
        assert defaults.dry_run is True
        assert defaults.quick_mode is True


class TestInstanceConfig:
    """Tests for InstanceConfig dataclass."""

    def test_required_fields(self):
        instance = InstanceConfig(
            name="sonarr",
            type="sonarr",
            url="http://localhost:8989",
            api_key="abc123",
            root_path="/media/tv",
        )
        assert instance.name == "sonarr"
        assert instance.type == "sonarr"
        assert instance.url == "http://localhost:8989"
        assert instance.api_key == "abc123"
        assert instance.root_path == "/media/tv"

    def test_default_values(self):
        instance = InstanceConfig(
            name="test",
            type="radarr",
            url="http://localhost:7878",
            api_key="key",
            root_path="/media/movies",
        )
        assert instance.target_languages == []
        assert instance.dry_run is False
        assert instance.quick_mode is False
        assert instance.target_genre is None

    def test_type_literal_accepts_sonarr(self):
        instance = InstanceConfig(
            name="test", type="sonarr", url="http://x", api_key="k", root_path="/p"
        )
        assert instance.type == "sonarr"

    def test_type_literal_accepts_radarr(self):
        instance = InstanceConfig(
            name="test", type="radarr", url="http://x", api_key="k", root_path="/p"
        )
        assert instance.type == "radarr"


class TestConfig:
    """Tests for Config dataclass."""

    def test_requires_defaults_and_instances(self):
        defaults = DefaultsConfig()
        instance = InstanceConfig(
            name="test", type="sonarr", url="http://x", api_key="k", root_path="/p"
        )
        config = Config(defaults=defaults, instances={"test": instance})
        assert config.defaults == defaults
        assert "test" in config.instances
        assert config.instances["test"] == instance
