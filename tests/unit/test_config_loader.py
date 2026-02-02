"""Tests for taggarr.config_loader module."""

import os
import pytest
from pathlib import Path

from taggarr.config_loader import (
    load_config, _parse_config, _interpolate, ConfigError
)


class TestInterpolate:
    """Tests for _interpolate function."""

    def test_returns_none_for_none(self):
        assert _interpolate(None) is None

    def test_returns_non_string_unchanged(self):
        assert _interpolate(123) == 123
        assert _interpolate(True) is True

    def test_returns_string_without_vars_unchanged(self):
        assert _interpolate("hello world") == "hello world"

    def test_interpolates_single_env_var(self, monkeypatch):
        monkeypatch.setenv("TEST_VAR", "test_value")
        result = _interpolate("${TEST_VAR}")
        assert result == "test_value"

    def test_interpolates_env_var_in_string(self, monkeypatch):
        monkeypatch.setenv("HOST", "localhost")
        result = _interpolate("http://${HOST}:8989")
        assert result == "http://localhost:8989"

    def test_interpolates_multiple_env_vars(self, monkeypatch):
        monkeypatch.setenv("HOST", "localhost")
        monkeypatch.setenv("PORT", "8989")
        result = _interpolate("http://${HOST}:${PORT}")
        assert result == "http://localhost:8989"

    def test_raises_for_missing_env_var(self):
        # Ensure var doesn't exist
        os.environ.pop("NONEXISTENT_VAR", None)
        with pytest.raises(ConfigError, match="Environment variable not set"):
            _interpolate("${NONEXISTENT_VAR}")


class TestParseConfig:
    """Tests for _parse_config function."""

    def test_parses_valid_config(self):
        config_path = Path(__file__).parent.parent / "fixtures" / "valid_config.yaml"
        config = _parse_config(config_path)

        assert config.defaults.target_languages == ["en", "ja"]
        assert "sonarr" in config.instances
        assert config.instances["sonarr"].url == "http://localhost:8989"

    def test_parses_minimal_config_with_defaults(self):
        config_path = Path(__file__).parent.parent / "fixtures" / "minimal_config.yaml"
        config = _parse_config(config_path)

        # Check defaults are applied
        assert config.defaults.target_languages == ["en"]
        assert config.defaults.dry_run is False

        # Check instance
        assert "radarr" in config.instances
        assert config.instances["radarr"].type == "radarr"

    def test_raises_for_no_instances(self, tmp_path):
        config_file = tmp_path / "empty.yaml"
        config_file.write_text("defaults:\n  dry_run: true\n")

        with pytest.raises(ConfigError, match="No instances configured"):
            _parse_config(config_file)

    def test_raises_for_missing_required_field(self, tmp_path):
        config_file = tmp_path / "missing.yaml"
        config_file.write_text("""
instances:
  test:
    type: sonarr
    url: http://localhost
    # missing api_key and root_path
""")
        with pytest.raises(ConfigError, match="missing required field"):
            _parse_config(config_file)

    def test_raises_for_invalid_instance_type(self, tmp_path):
        config_file = tmp_path / "invalid_type.yaml"
        config_file.write_text("""
instances:
  test:
    type: jellyfin
    url: http://localhost
    api_key: key
    root_path: /media
""")
        with pytest.raises(ConfigError, match="invalid type"):
            _parse_config(config_file)

    def test_strips_trailing_slash_from_url(self):
        config_path = Path(__file__).parent.parent / "fixtures" / "valid_config.yaml"
        config = _parse_config(config_path)
        assert not config.instances["sonarr"].url.endswith("/")

    def test_parses_target_languages_as_string(self, tmp_path):
        config_file = tmp_path / "string_langs.yaml"
        config_file.write_text("""
defaults:
  target_languages: "en, ja, de"
instances:
  test:
    type: sonarr
    url: http://localhost
    api_key: key
    root_path: /media
""")
        config = _parse_config(config_file)
        assert config.defaults.target_languages == ["en", "ja", "de"]

    def test_raises_for_invalid_yaml(self, tmp_path):
        config_file = tmp_path / "invalid.yaml"
        config_file.write_text("invalid: yaml: content: [unclosed")

        with pytest.raises(ConfigError, match="Invalid YAML"):
            _parse_config(config_file)

    def test_raises_for_non_dict_yaml(self, tmp_path):
        config_file = tmp_path / "list.yaml"
        config_file.write_text("- item1\n- item2")

        with pytest.raises(ConfigError, match="must be a YAML mapping"):
            _parse_config(config_file)

    def test_parses_instance_target_languages_as_string(self, tmp_path):
        config_file = tmp_path / "inst_string_langs.yaml"
        config_file.write_text("""
instances:
  test:
    type: sonarr
    url: http://localhost
    api_key: key
    root_path: /media
    target_languages: "fr, it"
""")
        config = _parse_config(config_file)
        assert config.instances["test"].target_languages == ["fr", "it"]

    def test_parses_target_genre(self, tmp_path):
        config_file = tmp_path / "genre.yaml"
        config_file.write_text("""
instances:
  test:
    type: sonarr
    url: http://localhost
    api_key: key
    root_path: /media
    target_genre: anime
""")
        config = _parse_config(config_file)
        assert config.instances["test"].target_genre == "anime"


class TestLoadConfig:
    """Tests for load_config function."""

    def test_loads_from_cli_path(self):
        config_path = str(Path(__file__).parent.parent / "fixtures" / "valid_config.yaml")
        config = load_config(cli_path=config_path)
        assert "sonarr" in config.instances

    def test_raises_for_nonexistent_cli_path(self):
        with pytest.raises(ConfigError, match="Config file not found"):
            load_config(cli_path="/nonexistent/path/config.yaml")

    def test_raises_when_no_config_found(self, tmp_path, monkeypatch):
        # Change to a directory with no config files
        monkeypatch.chdir(tmp_path)
        with pytest.raises(ConfigError, match="No config file found"):
            load_config()

    def test_loads_from_current_directory(self, tmp_path, monkeypatch):
        # Create a config file in tmp_path
        config_file = tmp_path / "taggarr.yaml"
        config_file.write_text("""
instances:
  test:
    type: sonarr
    url: http://localhost
    api_key: key
    root_path: /media
""")
        monkeypatch.chdir(tmp_path)
        config = load_config()
        assert "test" in config.instances


class TestGetConfigPaths:
    """Tests for config path resolution."""

    def test_xdg_config_home_takes_priority(self, tmp_path, monkeypatch):
        """XDG_CONFIG_HOME should be checked before ~/.config."""
        xdg_dir = tmp_path / "xdg"
        xdg_dir.mkdir()
        config_file = xdg_dir / "taggarr" / "config.yaml"
        config_file.parent.mkdir()
        config_file.write_text("""
instances:
  test:
    type: sonarr
    url: http://xdg-host
    api_key: key
    root_path: /media
""")
        monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg_dir))
        monkeypatch.chdir(tmp_path)  # No local taggarr.yaml

        config = load_config()
        assert config.instances["test"].url == "http://xdg-host"

    def test_falls_back_to_home_config_when_no_xdg(self, tmp_path, monkeypatch):
        """Should use ~/.config when XDG_CONFIG_HOME is not set."""
        # Unset XDG_CONFIG_HOME if present
        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)

        # Create config in fake home
        fake_home = tmp_path / "home"
        config_dir = fake_home / ".config" / "taggarr"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config.yaml"
        config_file.write_text("""
instances:
  test:
    type: sonarr
    url: http://home-config
    api_key: key
    root_path: /media
""")
        monkeypatch.setenv("HOME", str(fake_home))
        monkeypatch.chdir(tmp_path)  # No local taggarr.yaml

        config = load_config()
        assert config.instances["test"].url == "http://home-config"

    def test_appdata_on_windows(self, tmp_path, monkeypatch):
        """Should use APPDATA on Windows."""
        # Mock Windows platform
        monkeypatch.setattr("sys.platform", "win32")

        appdata_dir = tmp_path / "AppData" / "Roaming"
        config_dir = appdata_dir / "taggarr"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config.yaml"
        config_file.write_text("""
instances:
  test:
    type: sonarr
    url: http://appdata-host
    api_key: key
    root_path: /media
""")
        monkeypatch.setenv("APPDATA", str(appdata_dir))
        monkeypatch.chdir(tmp_path)  # No local taggarr.yaml

        config = load_config()
        assert config.instances["test"].url == "http://appdata-host"
