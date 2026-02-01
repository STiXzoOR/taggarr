# Test Coverage Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Achieve 100% test coverage for the taggarr codebase.

**Architecture:** Layered testing approach with pytest - unit tests using mocks for fast iteration (~90%), integration tests with real mediainfo binary (~10%). Tests mirror source structure in `tests/` directory.

**Tech Stack:** pytest, pytest-cov, pytest-mock, responses (HTTP mocking), temp directories for file operations.

---

## Task 1: Create pyproject.toml with Test Dependencies

**Files:**

- Create: `pyproject.toml`

**Step 1: Write pyproject.toml**

```toml
[project]
name = "taggarr"
version = "0.7.0"
description = "Dub Analysis & Tagging for Sonarr/Radarr"
requires-python = ">=3.9"
dependencies = [
    "requests>=2.32",
    "pymediainfo>=7.0",
    "pycountry>=24.6",
    "PyYAML>=6.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-cov>=4.0",
    "pytest-mock>=3.0",
    "responses>=0.23",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-v --cov=taggarr --cov-report=term-missing --cov-fail-under=100"
markers = [
    "integration: marks tests requiring external services (deselect with '-m not integration')",
]

[tool.coverage.run]
branch = true
source = ["taggarr"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "if __name__ == .__main__.:",
]
```

**Step 2: Verify file was created**

Run: `cat pyproject.toml | head -20`
Expected: Shows first 20 lines of pyproject.toml

**Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "build: add pyproject.toml with test dependencies"
```

---

## Task 2: Create Test Directory Structure and conftest.py

**Files:**

- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Create: `tests/unit/__init__.py`
- Create: `tests/unit/services/__init__.py`
- Create: `tests/unit/processors/__init__.py`
- Create: `tests/unit/storage/__init__.py`
- Create: `tests/integration/__init__.py`
- Create: `tests/fixtures/` (directory)

**Step 1: Create directory structure**

```bash
mkdir -p tests/unit/services tests/unit/processors tests/unit/storage tests/integration tests/fixtures
touch tests/__init__.py tests/unit/__init__.py tests/unit/services/__init__.py tests/unit/processors/__init__.py tests/unit/storage/__init__.py tests/integration/__init__.py
```

**Step 2: Write conftest.py with shared fixtures**

```python
"""Shared test fixtures for taggarr tests."""

import pytest
from unittest.mock import Mock
from taggarr.config_schema import (
    Config, DefaultsConfig, InstanceConfig, TagsConfig
)


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
```

**Step 3: Install dev dependencies**

Run: `pip install -e ".[dev]"`
Expected: Successfully installed pytest, pytest-cov, etc.

**Step 4: Verify pytest runs (no tests yet)**

Run: `pytest --collect-only`
Expected: "no tests ran" or similar (no errors)

**Step 5: Commit**

```bash
git add tests/ pyproject.toml
git commit -m "test: add test directory structure and conftest.py"
```

---

## Task 3: Add GitHub Actions CI Workflow

**Files:**

- Create: `.github/workflows/test.yml`

**Step 1: Create workflow directory**

```bash
mkdir -p .github/workflows
```

**Step 2: Write test workflow**

```yaml
name: Tests

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.9", "3.11", "3.12"]

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install mediainfo
        run: sudo apt-get install -y mediainfo

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[dev]"

      - name: Run tests
        run: pytest -m "not integration"

      - name: Upload coverage to Codecov
        if: matrix.python-version == '3.11'
        uses: codecov/codecov-action@v4
        with:
          fail_ci_if_error: false
```

**Step 3: Commit**

```bash
git add .github/
git commit -m "ci: add GitHub Actions test workflow"
```

---

## Task 4: Test languages.py (Pure Functions)

**Files:**

- Create: `tests/unit/test_languages.py`
- Reference: `taggarr/languages.py`

**Step 1: Write the failing tests**

```python
"""Tests for taggarr.languages module."""

import pytest
from taggarr import languages


class TestGetAliases:
    """Tests for get_aliases function."""

    def test_returns_empty_set_for_none(self):
        result = languages.get_aliases(None)
        assert result == set()

    def test_returns_empty_set_for_empty_string(self):
        result = languages.get_aliases("")
        assert result == set()

    def test_returns_aliases_for_alpha2_code(self):
        result = languages.get_aliases("en")
        assert "en" in result
        assert "eng" in result
        assert "english" in result

    def test_returns_aliases_for_alpha3_code(self):
        result = languages.get_aliases("eng")
        assert "en" in result
        assert "eng" in result

    def test_returns_aliases_for_language_name(self):
        result = languages.get_aliases("english")
        assert "en" in result
        assert "eng" in result

    def test_handles_case_insensitivity(self):
        result = languages.get_aliases("ENGLISH")
        assert "en" in result

    def test_includes_regional_variants(self):
        result = languages.get_aliases("en")
        assert "en-us" in result
        assert "en-gb" in result

    def test_returns_empty_set_for_unknown_language(self):
        result = languages.get_aliases("notareallanguage123")
        assert result == set()


class TestGetPrimaryCode:
    """Tests for get_primary_code function."""

    def test_returns_alpha2_for_language_name(self):
        result = languages.get_primary_code("English")
        assert result == "en"

    def test_returns_alpha2_for_alpha3_code(self):
        result = languages.get_primary_code("eng")
        assert result == "en"

    def test_returns_truncated_for_unknown(self):
        result = languages.get_primary_code("unknown")
        assert result == "un"

    def test_handles_japanese(self):
        result = languages.get_primary_code("Japanese")
        assert result == "ja"


class TestBuildLanguageCodes:
    """Tests for build_language_codes function."""

    def test_builds_codes_for_single_language(self):
        result = languages.build_language_codes(["en"])
        assert "en" in result
        assert "eng" in result
        assert "english" in result

    def test_builds_codes_for_multiple_languages(self):
        result = languages.build_language_codes(["en", "ja"])
        assert "en" in result
        assert "ja" in result
        assert "japanese" in result

    def test_returns_empty_set_for_empty_list(self):
        result = languages.build_language_codes([])
        assert result == set()
```

**Step 2: Run tests to verify they pass**

Run: `pytest tests/unit/test_languages.py -v`
Expected: All tests PASS

**Step 3: Commit**

```bash
git add tests/unit/test_languages.py
git commit -m "test: add tests for languages module"
```

---

## Task 5: Test config_schema.py (Dataclasses)

**Files:**

- Create: `tests/unit/test_config_schema.py`
- Reference: `taggarr/config_schema.py`

**Step 1: Write the failing tests**

```python
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
```

**Step 2: Run tests to verify they pass**

Run: `pytest tests/unit/test_config_schema.py -v`
Expected: All tests PASS

**Step 3: Commit**

```bash
git add tests/unit/test_config_schema.py
git commit -m "test: add tests for config_schema module"
```

---

## Task 6: Test config_loader.py (YAML Parsing)

**Files:**

- Create: `tests/unit/test_config_loader.py`
- Create: `tests/fixtures/valid_config.yaml`
- Create: `tests/fixtures/minimal_config.yaml`
- Reference: `taggarr/config_loader.py`

**Step 1: Create fixture files**

`tests/fixtures/valid_config.yaml`:

```yaml
defaults:
  target_languages: [en, ja]
  dry_run: false
  quick_mode: false
  log_level: INFO

instances:
  sonarr:
    type: sonarr
    url: http://localhost:8989
    api_key: test-key
    root_path: /media/tv
```

`tests/fixtures/minimal_config.yaml`:

```yaml
instances:
  radarr:
    type: radarr
    url: http://localhost:7878
    api_key: minimal-key
    root_path: /media/movies
```

**Step 2: Write the tests**

```python
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
```

**Step 3: Run tests to verify they pass**

Run: `pytest tests/unit/test_config_loader.py -v`
Expected: All tests PASS

**Step 4: Commit**

```bash
git add tests/unit/test_config_loader.py tests/fixtures/
git commit -m "test: add tests for config_loader module"
```

---

## Task 7: Test services/sonarr.py (HTTP Mocking)

**Files:**

- Create: `tests/unit/services/test_sonarr.py`
- Reference: `taggarr/services/sonarr.py`

**Step 1: Write the tests**

```python
"""Tests for taggarr.services.sonarr module."""

import pytest
import responses
from responses import matchers

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

        # Verify PUT was called with tag added
        put_call = [c for c in responses.calls if c.request.method == "PUT"][0]
        assert 1 in put_call.request.body.decode() or '"tags": [1]' in put_call.request.body.decode()

    def test_dry_run_does_not_call_api(self, client, caplog):
        # No responses mocked - would fail if API called
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

        # Verify tag was removed
        put_call = [c for c in responses.calls if c.request.method == "PUT"][0]
        assert "[]" in put_call.request.body.decode() or '"tags": []' in put_call.request.body.decode()

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
        client.refresh_series(42, dry_run=True)
        assert "Dry Run" in caplog.text


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
```

**Step 2: Run tests to verify they pass**

Run: `pytest tests/unit/services/test_sonarr.py -v`
Expected: All tests PASS

**Step 3: Commit**

```bash
git add tests/unit/services/test_sonarr.py
git commit -m "test: add tests for sonarr service"
```

---

## Task 8: Test services/radarr.py (HTTP Mocking)

**Files:**

- Create: `tests/unit/services/test_radarr.py`
- Reference: `taggarr/services/radarr.py`

**Step 1: Write the tests**

```python
"""Tests for taggarr.services.radarr module."""

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
    def test_returns_empty_list_on_error(self, client):
        responses.add(
            responses.GET,
            "http://radarr:7878/api/v3/movie",
            status=500,
        )

        result = client.get_movies()

        assert result == []


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
    def test_returns_none_when_not_found(self, client):
        responses.add(
            responses.GET,
            "http://radarr:7878/api/v3/movie",
            json=[],
        )

        result = client.get_movie_by_path("/nonexistent")

        assert result is None


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
        client.add_tag(42, "dub", dry_run=True)
        assert "Dry Run" in caplog.text


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
    def test_case_insensitive_matching(self, client):
        responses.add(
            responses.GET,
            "http://radarr:7878/api/v3/tag",
            json=[{"id": 3, "label": "DUB"}],
        )

        result = client._get_tag_id("dub")

        assert result == 3
```

**Step 2: Run tests to verify they pass**

Run: `pytest tests/unit/services/test_radarr.py -v`
Expected: All tests PASS

**Step 3: Commit**

```bash
git add tests/unit/services/test_radarr.py
git commit -m "test: add tests for radarr service"
```

---

## Task 9: Test services/media.py (Mediainfo Parsing)

**Files:**

- Create: `tests/unit/services/test_media.py`
- Reference: `taggarr/services/media.py`

**Step 1: Write the tests**

```python
"""Tests for taggarr.services.media module."""

import pytest
from unittest.mock import Mock, patch

from taggarr.services import media


class MockTrack:
    """Mock mediainfo track."""
    def __init__(self, track_type, language=None, title=None):
        self.track_type = track_type
        self.language = language
        self.title = title


class MockMediaInfo:
    """Mock MediaInfo result."""
    def __init__(self, tracks):
        self.tracks = tracks


class TestAnalyzeAudio:
    """Tests for analyze_audio function."""

    @patch("taggarr.services.media.MediaInfo.parse")
    def test_returns_language_codes_from_audio_tracks(self, mock_parse):
        mock_parse.return_value = MockMediaInfo([
            MockTrack("Audio", language="en"),
            MockTrack("Audio", language="ja"),
            MockTrack("Video"),  # Should be ignored
        ])

        result = media.analyze_audio("/path/to/video.mkv")

        assert sorted(result) == ["en", "ja"]

    @patch("taggarr.services.media.MediaInfo.parse")
    def test_returns_empty_list_on_no_audio_tracks(self, mock_parse):
        mock_parse.return_value = MockMediaInfo([
            MockTrack("Video"),
        ])

        result = media.analyze_audio("/path/to/video.mkv")

        assert result == []

    @patch("taggarr.services.media.MediaInfo.parse")
    def test_uses_fallback_for_unlabeled_main_track(self, mock_parse):
        mock_parse.return_value = MockMediaInfo([
            MockTrack("Audio", language="", title="Track 1"),
        ])

        result = media.analyze_audio("/path/to/video.mkv")

        assert "__fallback_original__" in result

    @patch("taggarr.services.media.MediaInfo.parse")
    def test_uses_fallback_for_empty_title_track(self, mock_parse):
        mock_parse.return_value = MockMediaInfo([
            MockTrack("Audio", language="", title=""),
        ])

        result = media.analyze_audio("/path/to/video.mkv")

        assert "__fallback_original__" in result

    @patch("taggarr.services.media.MediaInfo.parse")
    def test_uses_fallback_for_audio_1_title(self, mock_parse):
        mock_parse.return_value = MockMediaInfo([
            MockTrack("Audio", language=None, title="Audio 1"),
        ])

        result = media.analyze_audio("/path/to/video.mkv")

        assert "__fallback_original__" in result

    @patch("taggarr.services.media.MediaInfo.parse")
    def test_handles_mixed_labeled_and_unlabeled(self, mock_parse):
        mock_parse.return_value = MockMediaInfo([
            MockTrack("Audio", language="en"),
            MockTrack("Audio", language="", title="Track 1"),  # Fallback
        ])

        result = media.analyze_audio("/path/to/video.mkv")

        assert "en" in result
        assert "__fallback_original__" in result

    @patch("taggarr.services.media.MediaInfo.parse")
    def test_returns_empty_list_on_parse_error(self, mock_parse):
        mock_parse.side_effect = Exception("Parse error")

        result = media.analyze_audio("/path/to/video.mkv")

        assert result == []

    @patch("taggarr.services.media.MediaInfo.parse")
    def test_normalizes_language_to_lowercase(self, mock_parse):
        mock_parse.return_value = MockMediaInfo([
            MockTrack("Audio", language="EN"),
            MockTrack("Audio", language="  JA  "),
        ])

        result = media.analyze_audio("/path/to/video.mkv")

        assert "en" in result
        assert "ja" in result

    @patch("taggarr.services.media.MediaInfo.parse")
    def test_deduplicates_languages(self, mock_parse):
        mock_parse.return_value = MockMediaInfo([
            MockTrack("Audio", language="en"),
            MockTrack("Audio", language="en"),
        ])

        result = media.analyze_audio("/path/to/video.mkv")

        assert result.count("en") == 1
```

**Step 2: Run tests to verify they pass**

Run: `pytest tests/unit/services/test_media.py -v`
Expected: All tests PASS

**Step 3: Commit**

```bash
git add tests/unit/services/test_media.py
git commit -m "test: add tests for media service"
```

---

## Task 10: Test storage/json_store.py

**Files:**

- Create: `tests/unit/storage/test_json_store.py`
- Reference: `taggarr/storage/json_store.py`

**Step 1: Write the tests**

```python
"""Tests for taggarr.storage.json_store module."""

import json
import os
import pytest

from taggarr.storage import json_store


class TestLoad:
    """Tests for load function."""

    def test_returns_empty_dict_for_none_path(self):
        result = json_store.load(None)
        assert result == {"series": {}}

    def test_returns_empty_dict_for_nonexistent_file(self, tmp_path):
        result = json_store.load(str(tmp_path / "nonexistent.json"))
        assert result == {"series": {}}

    def test_loads_existing_json_file(self, tmp_path):
        json_path = tmp_path / "taggarr.json"
        data = {"series": {"show1": {"tag": "dub"}}}
        json_path.write_text(json.dumps(data))

        result = json_store.load(str(json_path))

        assert result["series"]["show1"]["tag"] == "dub"

    def test_uses_custom_key(self, tmp_path):
        json_path = tmp_path / "taggarr.json"
        data = {"movies": {"movie1": {"tag": "dub"}}}
        json_path.write_text(json.dumps(data))

        result = json_store.load(str(json_path), key="movies")

        assert "movies" in result

    def test_returns_empty_dict_for_none_path_with_custom_key(self):
        result = json_store.load(None, key="movies")
        assert result == {"movies": {}}

    def test_handles_corrupted_json(self, tmp_path):
        json_path = tmp_path / "taggarr.json"
        json_path.write_text("not valid json {{{")

        result = json_store.load(str(json_path))

        assert result == {"series": {}}
        # Should have created backup
        assert (tmp_path / "taggarr.json.bak").exists()


class TestSave:
    """Tests for save function."""

    def test_does_nothing_for_none_path(self, tmp_path):
        json_store.save(None, {"series": {}})
        # No error should be raised

    def test_saves_data_to_file(self, tmp_path):
        json_path = tmp_path / "taggarr.json"
        data = {"series": {"show1": {"tag": "dub"}}}

        json_store.save(str(json_path), data)

        assert json_path.exists()
        loaded = json.loads(json_path.read_text())
        assert loaded["series"]["show1"]["tag"] == "dub"

    def test_adds_version_to_saved_data(self, tmp_path):
        json_path = tmp_path / "taggarr.json"
        data = {"series": {}}

        json_store.save(str(json_path), data)

        loaded = json.loads(json_path.read_text())
        assert "version" in loaded

    def test_version_is_first_key(self, tmp_path):
        json_path = tmp_path / "taggarr.json"
        data = {"series": {"a": 1}}

        json_store.save(str(json_path), data)

        content = json_path.read_text()
        # Version should appear before series in the JSON
        assert content.index('"version"') < content.index('"series"')


class TestCompactLists:
    """Tests for _compact_lists function."""

    def test_compacts_episode_lists(self):
        raw = '[\n  "E01",\n  "E02",\n  "E03"\n]'
        result = json_store._compact_lists(raw)
        assert result == '["E01", "E02", "E03"]'

    def test_compacts_language_lists(self):
        raw = '"dub": [\n  "en",\n  "ja"\n]'
        result = json_store._compact_lists(raw)
        assert result == '"dub": ["en", "ja"]'

    def test_compacts_original_dub_list(self):
        raw = '"original_dub": [\n  "E01",\n  "E02"\n]'
        result = json_store._compact_lists(raw)
        assert '"original_dub": ["E01", "E02"]' in result

    def test_preserves_other_formatting(self):
        raw = '{\n  "name": "test",\n  "value": 123\n}'
        result = json_store._compact_lists(raw)
        assert result == raw
```

**Step 2: Run tests to verify they pass**

Run: `pytest tests/unit/storage/test_json_store.py -v`
Expected: All tests PASS

**Step 3: Commit**

```bash
git add tests/unit/storage/test_json_store.py
git commit -m "test: add tests for json_store module"
```

---

## Task 11: Test nfo.py (NFO Parsing)

**Files:**

- Create: `tests/unit/test_nfo.py`
- Reference: `taggarr/nfo.py`

**Step 1: Write the tests**

```python
"""Tests for taggarr.nfo module."""

import pytest
import xml.etree.ElementTree as ET

from taggarr import nfo


class TestSafeParse:
    """Tests for safe_parse function."""

    def test_parses_valid_tvshow_nfo(self, tmp_path):
        nfo_path = tmp_path / "tvshow.nfo"
        nfo_path.write_text("<tvshow><title>Test Show</title></tvshow>")

        root = nfo.safe_parse(str(nfo_path))

        assert root.tag == "tvshow"
        assert root.find("title").text == "Test Show"

    def test_handles_duplicate_closing_tags(self, tmp_path):
        nfo_path = tmp_path / "tvshow.nfo"
        # Corrupted file with duplicate closing tag
        nfo_path.write_text("<tvshow><title>Test</title></tvshow></tvshow>garbage")

        root = nfo.safe_parse(str(nfo_path))

        assert root.tag == "tvshow"

    def test_raises_for_invalid_xml(self, tmp_path):
        nfo_path = tmp_path / "bad.nfo"
        nfo_path.write_text("not xml at all")

        with pytest.raises(ET.ParseError):
            nfo.safe_parse(str(nfo_path))


class TestGetGenres:
    """Tests for get_genres function."""

    def test_returns_genres_from_nfo(self, tmp_path):
        nfo_path = tmp_path / "tvshow.nfo"
        nfo_path.write_text("""
<tvshow>
    <genre>Action</genre>
    <genre>Drama</genre>
    <genre>Anime</genre>
</tvshow>
""")

        result = nfo.get_genres(str(nfo_path))

        assert "action" in result
        assert "drama" in result
        assert "anime" in result

    def test_returns_empty_list_for_no_genres(self, tmp_path):
        nfo_path = tmp_path / "tvshow.nfo"
        nfo_path.write_text("<tvshow><title>Test</title></tvshow>")

        result = nfo.get_genres(str(nfo_path))

        assert result == []

    def test_returns_empty_list_on_parse_error(self, tmp_path):
        nfo_path = tmp_path / "bad.nfo"
        nfo_path.write_text("invalid xml")

        result = nfo.get_genres(str(nfo_path))

        assert result == []


class TestUpdateTag:
    """Tests for update_tag function."""

    def test_adds_tag_to_nfo(self, tmp_path):
        nfo_path = tmp_path / "tvshow.nfo"
        nfo_path.write_text("<tvshow><title>Test</title></tvshow>")

        nfo.update_tag(str(nfo_path), "dub")

        content = nfo_path.read_text()
        assert "<tag>dub</tag>" in content

    def test_removes_existing_managed_tags(self, tmp_path):
        nfo_path = tmp_path / "tvshow.nfo"
        nfo_path.write_text("""<tvshow>
<tag>semi-dub</tag>
<tag>wrong-dub</tag>
<title>Test</title>
</tvshow>""")

        nfo.update_tag(str(nfo_path), "dub")

        content = nfo_path.read_text()
        assert "semi-dub" not in content
        assert "wrong-dub" not in content
        assert "<tag>dub</tag>" in content

    def test_preserves_non_managed_tags(self, tmp_path):
        nfo_path = tmp_path / "tvshow.nfo"
        nfo_path.write_text("""<tvshow>
<tag>custom-tag</tag>
<title>Test</title>
</tvshow>""")

        nfo.update_tag(str(nfo_path), "dub")

        content = nfo_path.read_text()
        assert "custom-tag" in content
        assert "<tag>dub</tag>" in content

    def test_dry_run_does_not_modify_file(self, tmp_path, caplog):
        nfo_path = tmp_path / "tvshow.nfo"
        original = "<tvshow><title>Test</title></tvshow>"
        nfo_path.write_text(original)

        nfo.update_tag(str(nfo_path), "dub", dry_run=True)

        assert nfo_path.read_text() == original
        assert "Dry Run" in caplog.text


class TestUpdateMovieTag:
    """Tests for update_movie_tag function."""

    def test_adds_tag_to_movie_nfo(self, tmp_path):
        nfo_path = tmp_path / "movie.nfo"
        nfo_path.write_text("<movie><title>Test Movie</title></movie>")

        nfo.update_movie_tag(str(nfo_path), "dub")

        content = nfo_path.read_text()
        assert "<tag>dub</tag>" in content


class TestUpdateGenre:
    """Tests for update_genre function."""

    def test_adds_dub_genre_when_should_have(self, tmp_path):
        nfo_path = tmp_path / "tvshow.nfo"
        nfo_path.write_text("<tvshow><genre>Action</genre></tvshow>")

        nfo.update_genre(str(nfo_path), should_have_dub=True)

        content = nfo_path.read_text()
        assert "<genre>Dub</genre>" in content

    def test_removes_dub_genre_when_should_not_have(self, tmp_path):
        nfo_path = tmp_path / "tvshow.nfo"
        nfo_path.write_text("<tvshow><genre>Dub</genre><genre>Action</genre></tvshow>")

        nfo.update_genre(str(nfo_path), should_have_dub=False)

        content = nfo_path.read_text()
        assert "Dub" not in content
        assert "Action" in content

    def test_does_nothing_when_already_correct(self, tmp_path):
        nfo_path = tmp_path / "tvshow.nfo"
        original = "<tvshow><genre>Dub</genre></tvshow>"
        nfo_path.write_text(original)

        nfo.update_genre(str(nfo_path), should_have_dub=True)

        # File should be unchanged (already has Dub)
        assert "<genre>Dub</genre>" in nfo_path.read_text()

    def test_dry_run_does_not_modify_file(self, tmp_path, caplog):
        nfo_path = tmp_path / "tvshow.nfo"
        original = "<tvshow><genre>Action</genre></tvshow>"
        nfo_path.write_text(original)

        nfo.update_genre(str(nfo_path), should_have_dub=True, dry_run=True)

        assert "Dub" not in nfo_path.read_text()
        assert "Dry Run" in caplog.text
```

**Step 2: Run tests to verify they pass**

Run: `pytest tests/unit/test_nfo.py -v`
Expected: All tests PASS

**Step 3: Commit**

```bash
git add tests/unit/test_nfo.py
git commit -m "test: add tests for nfo module"
```

---

## Task 12: Test processors/tv.py (Business Logic)

**Files:**

- Create: `tests/unit/processors/test_tv.py`
- Reference: `taggarr/processors/tv.py`

**Step 1: Write the tests**

```python
"""Tests for taggarr.processors.tv module."""

import os
import pytest
from unittest.mock import Mock, patch, MagicMock
from types import SimpleNamespace

from taggarr.processors import tv
from taggarr.config_schema import InstanceConfig, TagsConfig


@pytest.fixture
def opts():
    """Default command line options."""
    return SimpleNamespace(quick=False, dry_run=False, write_mode=0)


@pytest.fixture
def instance():
    """Sonarr instance config."""
    return InstanceConfig(
        name="test",
        type="sonarr",
        url="http://sonarr:8989",
        api_key="key",
        root_path="/media/tv",
        target_languages=["en"],
        tags=TagsConfig(),
        dry_run=False,
        quick_mode=False,
        target_genre=None,
    )


class TestDetermineStatus:
    """Tests for _determine_status function."""

    def test_returns_wrong_dub_when_unexpected_languages(self):
        stats = {"unexpected_languages": ["de"], "dub": ["E01"], "missing_dub": []}

        result = tv._determine_status(stats)

        assert result == "wrong-dub"

    def test_returns_fully_dub_when_all_episodes_dubbed(self):
        stats = {"unexpected_languages": [], "dub": ["E01", "E02"], "missing_dub": []}

        result = tv._determine_status(stats)

        assert result == "fully-dub"

    def test_returns_semi_dub_when_some_missing(self):
        stats = {"unexpected_languages": [], "dub": ["E01"], "missing_dub": ["E02"]}

        result = tv._determine_status(stats)

        assert result == "semi-dub"

    def test_returns_original_when_no_dub(self):
        stats = {"unexpected_languages": [], "dub": [], "missing_dub": []}

        result = tv._determine_status(stats)

        assert result == "original"


class TestPassesGenreFilter:
    """Tests for _passes_genre_filter function."""

    def test_returns_true_when_no_filter(self, tmp_path):
        nfo_path = tmp_path / "tvshow.nfo"
        nfo_path.write_text("<tvshow><genre>Action</genre></tvshow>")

        result = tv._passes_genre_filter(str(nfo_path), None)

        assert result is True

    def test_returns_true_when_genre_matches(self, tmp_path):
        nfo_path = tmp_path / "tvshow.nfo"
        nfo_path.write_text("<tvshow><genre>Anime</genre></tvshow>")

        result = tv._passes_genre_filter(str(nfo_path), "anime")

        assert result is True

    def test_returns_false_when_genre_not_found(self, tmp_path):
        nfo_path = tmp_path / "tvshow.nfo"
        nfo_path.write_text("<tvshow><genre>Drama</genre></tvshow>")

        result = tv._passes_genre_filter(str(nfo_path), "anime")

        assert result is False


class TestHasChanges:
    """Tests for _has_changes function."""

    def test_returns_true_when_season_modified(self, tmp_path):
        show_path = tmp_path / "Show"
        season_path = show_path / "Season 01"
        season_path.mkdir(parents=True)

        saved_seasons = {"Season 01": {"last_modified": 0}}

        result = tv._has_changes(str(show_path), saved_seasons)

        assert result is True

    def test_returns_false_when_no_changes(self, tmp_path):
        show_path = tmp_path / "Show"
        season_path = show_path / "Season 01"
        season_path.mkdir(parents=True)

        current_mtime = os.path.getmtime(str(season_path))
        saved_seasons = {"Season 01": {"last_modified": current_mtime + 1}}

        result = tv._has_changes(str(show_path), saved_seasons)

        assert result is False


class TestHasNewSeasons:
    """Tests for _has_new_seasons function."""

    def test_returns_true_when_new_season_exists(self, tmp_path):
        show_path = tmp_path / "Show"
        (show_path / "Season 01").mkdir(parents=True)
        (show_path / "Season 02").mkdir(parents=True)

        saved_seasons = {"Season 01": {}}

        result = tv._has_new_seasons(str(show_path), saved_seasons)

        assert result is True

    def test_returns_false_when_no_new_seasons(self, tmp_path):
        show_path = tmp_path / "Show"
        (show_path / "Season 01").mkdir(parents=True)

        saved_seasons = {"Season 01": {}}

        result = tv._has_new_seasons(str(show_path), saved_seasons)

        assert result is False


class TestApplyTags:
    """Tests for _apply_tags function."""

    def test_adds_dub_tag_and_removes_others(self, instance):
        client = Mock()

        tv._apply_tags(client, 1, instance.tags.dub, instance, False)

        client.add_tag.assert_called_once_with(1, "dub", False)
        assert client.remove_tag.call_count == 2  # Removes wrong and semi

    def test_adds_semi_tag_and_removes_others(self, instance):
        client = Mock()

        tv._apply_tags(client, 1, instance.tags.semi, instance, False)

        client.add_tag.assert_called_once_with(1, "semi-dub", False)
        assert client.remove_tag.call_count == 2

    def test_adds_wrong_tag_and_removes_others(self, instance):
        client = Mock()

        tv._apply_tags(client, 1, instance.tags.wrong, instance, False)

        client.add_tag.assert_called_once_with(1, "wrong-dub", False)
        assert client.remove_tag.call_count == 2

    def test_removes_all_tags_when_no_tag(self, instance):
        client = Mock()

        tv._apply_tags(client, 1, None, instance, False)

        client.add_tag.assert_not_called()
        assert client.remove_tag.call_count == 3


class TestBuildEntry:
    """Tests for _build_entry function."""

    def test_builds_entry_with_all_fields(self):
        series = {"originalLanguage": {"name": "Japanese"}}
        seasons = {"Season 01": {"status": "fully-dub"}}

        result = tv._build_entry("Test Show", "dub", seasons, series, 12345.0)

        assert result["display_name"] == "Test Show"
        assert result["tag"] == "dub"
        assert result["original_language"] == "japanese"
        assert result["seasons"] == seasons
        assert result["last_modified"] == 12345.0
        assert "last_scan" in result

    def test_handles_string_original_language(self):
        series = {"originalLanguage": "English"}

        result = tv._build_entry("Test", "dub", {}, series, 0)

        assert result["original_language"] == "english"

    def test_uses_none_string_when_no_tag(self):
        series = {"originalLanguage": "English"}

        result = tv._build_entry("Test", None, {}, series, 0)

        assert result["tag"] == "none"
```

**Step 2: Run tests to verify they pass**

Run: `pytest tests/unit/processors/test_tv.py -v`
Expected: All tests PASS

**Step 3: Commit**

```bash
git add tests/unit/processors/test_tv.py
git commit -m "test: add tests for tv processor"
```

---

## Task 13: Test processors/movies.py (Business Logic)

**Files:**

- Create: `tests/unit/processors/test_movies.py`
- Reference: `taggarr/processors/movies.py`

**Step 1: Write the tests**

```python
"""Tests for taggarr.processors.movies module."""

import pytest
from unittest.mock import Mock, patch
from types import SimpleNamespace

from taggarr.processors import movies
from taggarr.config_schema import InstanceConfig, TagsConfig


@pytest.fixture
def instance():
    """Radarr instance config."""
    return InstanceConfig(
        name="test",
        type="radarr",
        url="http://radarr:7878",
        api_key="key",
        root_path="/media/movies",
        target_languages=["en"],
        tags=TagsConfig(),
        dry_run=False,
        quick_mode=False,
        target_genre=None,
    )


class TestDetermineTag:
    """Tests for _determine_tag function."""

    def test_returns_none_for_none_scan_result(self, instance):
        result = movies._determine_tag(None, instance, {"en"})
        assert result is None

    def test_returns_none_for_fallback_original(self, instance):
        scan_result = {
            "languages": ["__fallback_original__"],
            "original_codes": {"ja"},
        }

        result = movies._determine_tag(scan_result, instance, {"en"})

        assert result is None

    def test_returns_dub_when_all_targets_present(self, instance):
        scan_result = {
            "languages": ["en", "ja"],
            "original_codes": {"ja"},
        }

        result = movies._determine_tag(scan_result, instance, {"en", "eng", "english"})

        assert result == "dub"

    def test_returns_wrong_when_unexpected_language(self, instance):
        scan_result = {
            "languages": ["en", "de"],  # German is unexpected
            "original_codes": {"ja"},
        }

        result = movies._determine_tag(scan_result, instance, {"en", "eng"})

        assert result == "wrong-dub"

    def test_returns_none_when_original_only(self, instance):
        scan_result = {
            "languages": ["ja"],
            "original_codes": {"ja", "jpn", "japanese"},
        }

        result = movies._determine_tag(scan_result, instance, {"en"})

        assert result is None


class TestFindNfo:
    """Tests for _find_nfo function."""

    def test_finds_movie_nfo(self, tmp_path):
        movie_path = tmp_path / "Inception (2010)"
        movie_path.mkdir()
        (movie_path / "movie.nfo").write_text("<movie/>")

        result = movies._find_nfo(str(movie_path), "Inception (2010)")

        assert result is not None
        assert result.endswith("movie.nfo")

    def test_finds_named_nfo(self, tmp_path):
        movie_path = tmp_path / "Inception (2010)"
        movie_path.mkdir()
        (movie_path / "Inception (2010).nfo").write_text("<movie/>")

        result = movies._find_nfo(str(movie_path), "Inception (2010)")

        assert result is not None
        assert "Inception" in result

    def test_returns_none_when_no_nfo(self, tmp_path):
        movie_path = tmp_path / "Inception (2010)"
        movie_path.mkdir()

        result = movies._find_nfo(str(movie_path), "Inception (2010)")

        assert result is None

    def test_prefers_movie_nfo_over_named(self, tmp_path):
        movie_path = tmp_path / "Inception (2010)"
        movie_path.mkdir()
        (movie_path / "movie.nfo").write_text("<movie/>")
        (movie_path / "Inception (2010).nfo").write_text("<movie/>")

        result = movies._find_nfo(str(movie_path), "Inception (2010)")

        assert result.endswith("movie.nfo")


class TestScanMovie:
    """Tests for _scan_movie function."""

    @patch("taggarr.processors.movies.media.analyze_audio")
    def test_returns_scan_result_for_valid_movie(self, mock_analyze, tmp_path, instance):
        movie_path = tmp_path / "Inception (2010)"
        movie_path.mkdir()
        video_file = movie_path / "Inception.2010.mkv"
        video_file.write_bytes(b"x" * 1000)  # Fake video file

        mock_analyze.return_value = ["en", "ja"]
        movie_meta = {"originalLanguage": {"name": "English"}}

        result = movies._scan_movie(str(movie_path), movie_meta, instance, {"en"})

        assert result is not None
        assert "en" in result["languages"]
        assert result["original_language"] == "english"

    @patch("taggarr.processors.movies.media.analyze_audio")
    def test_returns_none_when_no_video_files(self, mock_analyze, tmp_path, instance):
        movie_path = tmp_path / "Empty Movie"
        movie_path.mkdir()

        movie_meta = {"originalLanguage": "English"}

        result = movies._scan_movie(str(movie_path), movie_meta, instance, {"en"})

        assert result is None

    @patch("taggarr.processors.movies.media.analyze_audio")
    def test_ignores_sample_files(self, mock_analyze, tmp_path, instance):
        movie_path = tmp_path / "Movie"
        movie_path.mkdir()
        (movie_path / "sample.mkv").write_bytes(b"x" * 100)
        (movie_path / "Movie.mkv").write_bytes(b"x" * 1000)

        mock_analyze.return_value = ["en"]
        movie_meta = {"originalLanguage": "English"}

        result = movies._scan_movie(str(movie_path), movie_meta, instance, {"en"})

        # Should have scanned the larger file, not the sample
        assert "Movie.mkv" in result["file"]

    @patch("taggarr.processors.movies.media.analyze_audio")
    def test_scans_largest_video_file(self, mock_analyze, tmp_path, instance):
        movie_path = tmp_path / "Movie"
        movie_path.mkdir()
        (movie_path / "small.mkv").write_bytes(b"x" * 100)
        (movie_path / "main.mkv").write_bytes(b"x" * 10000)
        (movie_path / "medium.mkv").write_bytes(b"x" * 1000)

        mock_analyze.return_value = ["en"]
        movie_meta = {"originalLanguage": "English"}

        result = movies._scan_movie(str(movie_path), movie_meta, instance, {"en"})

        assert result["file"] == "main.mkv"
```

**Step 2: Run tests to verify they pass**

Run: `pytest tests/unit/processors/test_movies.py -v`
Expected: All tests PASS

**Step 3: Commit**

```bash
git add tests/unit/processors/test_movies.py
git commit -m "test: add tests for movies processor"
```

---

## Task 14: Test logging_setup.py

**Files:**

- Create: `tests/unit/test_logging_setup.py`
- Reference: `taggarr/logging_setup.py`

**Step 1: Write the tests**

```python
"""Tests for taggarr.logging_setup module."""

import logging
import pytest

from taggarr.logging_setup import setup_logging


class TestSetupLogging:
    """Tests for setup_logging function."""

    def test_creates_logger_with_name(self, tmp_path):
        logger = setup_logging(path=str(tmp_path))

        assert logger.name == "taggarr"

    def test_sets_log_level_from_string(self, tmp_path):
        logger = setup_logging(level="DEBUG", path=str(tmp_path))

        assert logger.level == logging.DEBUG

    def test_defaults_to_info_for_invalid_level(self, tmp_path):
        logger = setup_logging(level="INVALID", path=str(tmp_path))

        assert logger.level == logging.INFO

    def test_creates_log_directory(self, tmp_path):
        log_path = tmp_path / "nested" / "logs"

        setup_logging(path=str(log_path))

        assert log_path.exists()

    def test_creates_log_file(self, tmp_path):
        setup_logging(path=str(tmp_path))

        log_files = list(tmp_path.glob("taggarr*.log"))
        assert len(log_files) == 1

    def test_adds_file_and_stream_handlers(self, tmp_path):
        # Clear any existing handlers
        logger = logging.getLogger("taggarr")
        logger.handlers.clear()

        logger = setup_logging(path=str(tmp_path))

        handler_types = [type(h).__name__ for h in logger.handlers]
        assert "FileHandler" in handler_types
        assert "StreamHandler" in handler_types
```

**Step 2: Run tests to verify they pass**

Run: `pytest tests/unit/test_logging_setup.py -v`
Expected: All tests PASS

**Step 3: Commit**

```bash
git add tests/unit/test_logging_setup.py
git commit -m "test: add tests for logging_setup module"
```

---

## Task 15: Test taggarr/**init**.py (Entry Points)

**Files:**

- Create: `tests/unit/test_init.py`
- Reference: `taggarr/__init__.py`

**Step 1: Write the tests**

```python
"""Tests for taggarr package entry points."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from types import SimpleNamespace

from taggarr import run, run_loop, _process_instance
from taggarr.config_schema import Config, DefaultsConfig, InstanceConfig, TagsConfig


@pytest.fixture
def opts():
    """Default command line options."""
    return SimpleNamespace(
        quick=False,
        dry_run=False,
        write_mode=0,
        instances=None,
    )


@pytest.fixture
def config(tmp_path):
    """Test configuration."""
    return Config(
        defaults=DefaultsConfig(log_path=str(tmp_path)),
        instances={
            "sonarr": InstanceConfig(
                name="sonarr",
                type="sonarr",
                url="http://sonarr:8989",
                api_key="key",
                root_path=str(tmp_path / "tv"),
                target_languages=["en"],
                tags=TagsConfig(),
            ),
        },
    )


class TestRun:
    """Tests for run function."""

    @patch("taggarr._process_instance")
    @patch("taggarr.setup_logging")
    def test_processes_all_instances(self, mock_logging, mock_process, opts, config, tmp_path):
        mock_logging.return_value = MagicMock()
        (tmp_path / "tv").mkdir()

        run(opts, config)

        mock_process.assert_called_once()

    @patch("taggarr._process_instance")
    @patch("taggarr.setup_logging")
    def test_filters_instances_when_specified(self, mock_logging, mock_process, opts, config, tmp_path):
        mock_logging.return_value = MagicMock()
        opts.instances = "nonexistent"

        run(opts, config)

        mock_process.assert_not_called()

    @patch("taggarr._process_instance")
    @patch("taggarr.setup_logging")
    def test_logs_quick_mode(self, mock_logging, mock_process, opts, config, tmp_path, caplog):
        mock_logger = MagicMock()
        mock_logging.return_value = mock_logger
        opts.quick = True
        (tmp_path / "tv").mkdir()

        run(opts, config)

        # Check quick mode was logged
        mock_logger.info.assert_any_call("Quick mode: Scanning only first episode per season.")


class TestProcessInstance:
    """Tests for _process_instance function."""

    @patch("taggarr.tv.process_all")
    @patch("taggarr.json_store.save")
    @patch("taggarr.json_store.load")
    @patch("taggarr.SonarrClient")
    def test_processes_sonarr_instance(self, mock_client, mock_load, mock_save, mock_process, opts, tmp_path):
        instance = InstanceConfig(
            name="sonarr",
            type="sonarr",
            url="http://sonarr:8989",
            api_key="key",
            root_path=str(tmp_path),
            target_languages=["en"],
            tags=TagsConfig(),
        )
        mock_load.return_value = {"series": {}}
        mock_process.return_value = {"series": {}}

        _process_instance(instance, opts)

        mock_client.assert_called_once_with("http://sonarr:8989", "key")
        mock_process.assert_called_once()
        mock_save.assert_called_once()

    @patch("taggarr.movies.process_all")
    @patch("taggarr.json_store.save")
    @patch("taggarr.json_store.load")
    @patch("taggarr.RadarrClient")
    def test_processes_radarr_instance(self, mock_client, mock_load, mock_save, mock_process, opts, tmp_path):
        instance = InstanceConfig(
            name="radarr",
            type="radarr",
            url="http://radarr:7878",
            api_key="key",
            root_path=str(tmp_path),
            target_languages=["en"],
            tags=TagsConfig(),
        )
        mock_load.return_value = {"movies": {}}
        mock_process.return_value = {"movies": {}}

        _process_instance(instance, opts)

        mock_client.assert_called_once_with("http://radarr:7878", "key")
        mock_process.assert_called_once()


class TestRunLoop:
    """Tests for run_loop function."""

    @patch("taggarr.time.sleep")
    @patch("taggarr.run")
    def test_calls_run_repeatedly(self, mock_run, mock_sleep, opts, config):
        # Make sleep raise to break the loop
        mock_sleep.side_effect = [None, KeyboardInterrupt]

        with pytest.raises(KeyboardInterrupt):
            run_loop(opts, config)

        assert mock_run.call_count == 2
        mock_sleep.assert_called_with(config.defaults.run_interval_seconds)
```

**Step 2: Run tests to verify they pass**

Run: `pytest tests/unit/test_init.py -v`
Expected: All tests PASS

**Step 3: Commit**

```bash
git add tests/unit/test_init.py
git commit -m "test: add tests for package entry points"
```

---

## Task 16: Run Full Test Suite and Check Coverage

**Step 1: Run all tests with coverage**

Run: `pytest --cov=taggarr --cov-report=term-missing --cov-report=html`
Expected: Shows coverage report with any gaps

**Step 2: Open coverage report**

Run: `open htmlcov/index.html` (macOS) or `xdg-open htmlcov/index.html` (Linux)
Expected: Browser shows detailed coverage report

**Step 3: Identify uncovered lines**

Review the HTML report to find any uncovered lines. Common gaps:

- Exception handlers
- Edge cases in conditionals
- Error logging paths

**Step 4: Add tests for any gaps**

For each uncovered line/branch, add a test case to the appropriate test file.

**Step 5: Re-run until 100%**

Run: `pytest --cov=taggarr --cov-report=term-missing --cov-fail-under=100`
Expected: All tests pass, 100% coverage

**Step 6: Final commit**

```bash
git add -A
git commit -m "test: achieve 100% test coverage"
```

---

## Task 17: Create Integration Test

**Files:**

- Create: `tests/integration/test_smoke.py`

**Step 1: Write integration test**

```python
"""Integration smoke test for taggarr."""

import os
import pytest
from unittest.mock import patch, Mock
from types import SimpleNamespace

from taggarr import run
from taggarr.config_schema import Config, DefaultsConfig, InstanceConfig, TagsConfig


@pytest.fixture
def integration_config(tmp_path):
    """Config for integration testing."""
    tv_path = tmp_path / "tv"
    tv_path.mkdir()

    # Create a minimal show structure
    show_path = tv_path / "Test Show"
    season_path = show_path / "Season 01"
    season_path.mkdir(parents=True)

    # Create NFO file
    nfo_content = "<tvshow><title>Test Show</title><genre>Drama</genre></tvshow>"
    (show_path / "tvshow.nfo").write_text(nfo_content)

    return Config(
        defaults=DefaultsConfig(log_path=str(tmp_path / "logs")),
        instances={
            "test-sonarr": InstanceConfig(
                name="test-sonarr",
                type="sonarr",
                url="http://localhost:8989",
                api_key="test-key",
                root_path=str(tv_path),
                target_languages=["en"],
                tags=TagsConfig(),
                dry_run=True,  # Always dry run in tests
            ),
        },
    )


@pytest.mark.integration
class TestSmoke:
    """Smoke tests for end-to-end functionality."""

    @patch("taggarr.services.sonarr.requests")
    def test_full_scan_with_mocked_api(self, mock_requests, integration_config, tmp_path):
        """Test a full scan cycle with mocked Sonarr API."""
        # Mock Sonarr API responses
        mock_response = Mock()
        mock_response.json.return_value = [
            {
                "id": 1,
                "title": "Test Show",
                "path": str(tmp_path / "tv" / "Test Show"),
                "originalLanguage": {"name": "English"},
                "tags": [],
            }
        ]
        mock_requests.get.return_value = mock_response

        opts = SimpleNamespace(
            quick=True,
            dry_run=True,
            write_mode=0,
            instances=None,
        )

        # Should not raise any exceptions
        run(opts, integration_config)
```

**Step 2: Run integration test**

Run: `pytest tests/integration/ -v -m integration`
Expected: Integration test passes

**Step 3: Commit**

```bash
git add tests/integration/
git commit -m "test: add integration smoke test"
```

---

## Task 18: Final Verification and PR

**Step 1: Run full test suite one more time**

Run: `pytest -v --cov=taggarr --cov-fail-under=100`
Expected: All tests pass with 100% coverage

**Step 2: Verify CI would pass**

Run: `pytest -m "not integration" -v`
Expected: All unit tests pass

**Step 3: Create final commit if needed**

```bash
git status
# If any changes:
git add -A
git commit -m "test: finalize test suite"
```

**Step 4: Push branch and create PR**

```bash
git push -u origin feature/test-coverage
gh pr create --title "Add 100% test coverage" --body "$(cat <<'EOF'
## Summary
- Added pytest with pytest-cov for testing
- Created comprehensive unit tests for all modules
- Added GitHub Actions CI workflow
- Achieved 100% test coverage

## Test plan
- [x] All unit tests pass locally
- [x] Coverage report shows 100%
- [ ] CI passes on PR

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```
