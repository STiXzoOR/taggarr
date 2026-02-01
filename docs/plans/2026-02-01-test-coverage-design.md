# Test Coverage Design

**Goal:** 100% test coverage for taggarr

**Date:** 2026-02-01

## Decisions

- **Framework:** pytest with pytest-cov
- **Mocking approach:** Layered (unit tests with mocks + small integration suite)
- **CI:** GitHub Actions with coverage enforcement
- **Test location:** Separate `tests/` directory mirroring source structure

## Project Structure

```
taggarr/
├── pyproject.toml              # Project config + pytest settings
├── tests/
│   ├── conftest.py             # Shared fixtures (mock clients, sample data)
│   ├── fixtures/               # Static test data
│   │   ├── sample.yaml         # Test config files
│   │   ├── sonarr_responses/   # Mocked API responses
│   │   ├── radarr_responses/
│   │   └── media_samples/      # Small test video files or mediainfo output
│   ├── unit/                   # Fast, isolated tests (~90%)
│   │   ├── test_config_loader.py
│   │   ├── test_config_schema.py
│   │   ├── test_languages.py
│   │   ├── test_nfo.py
│   │   ├── services/
│   │   │   ├── test_sonarr.py
│   │   │   ├── test_radarr.py
│   │   │   └── test_media.py
│   │   ├── processors/
│   │   │   ├── test_tv.py
│   │   │   └── test_movies.py
│   │   └── storage/
│   │       └── test_json_store.py
│   └── integration/            # Real dependencies (~10%)
│       └── test_smoke.py       # End-to-end with real mediainfo
└── .github/
    └── workflows/
        └── test.yml            # CI pipeline
```

## Dependencies & Configuration

**pyproject.toml:**

```toml
[project]
name = "taggarr"
version = "0.7.0"
requires-python = ">=3.7"
dependencies = [
    "requests",
    "pymediainfo",
    "pycountry",
    "PyYAML",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-cov>=4.0",
    "pytest-mock>=3.0",
    "responses>=0.23",      # Mock HTTP requests elegantly
    "freezegun>=1.2",       # Mock datetime if needed
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
omit = ["taggarr/__main__.py"]  # Entry point, minimal logic

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "if __name__ == .__main__.:",
]
```

## GitHub Actions CI

**.github/workflows/test.yml:**

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
        run: pytest

      - name: Upload coverage to Codecov
        if: matrix.python-version == '3.11'
        uses: codecov/codecov-action@v4
        with:
          fail_ci_if_error: true
```

## Testing Strategy by Module

| Module                  | Test Approach                      | Key Scenarios                                                       |
| ----------------------- | ---------------------------------- | ------------------------------------------------------------------- |
| `config_loader.py`      | Unit with fixture YAML files       | Valid config, missing fields, env var interpolation, file not found |
| `config_schema.py`      | Unit, pure dataclasses             | Defaults applied correctly, validation                              |
| `languages.py`          | Unit, pure functions               | Language code normalization, edge cases                             |
| `nfo.py`                | Unit with temp files               | Read/write NFO, malformed XML, missing files                        |
| `services/sonarr.py`    | Unit with `responses` mock         | API calls, error handling, tag operations                           |
| `services/radarr.py`    | Unit with `responses` mock         | Same as Sonarr                                                      |
| `services/media.py`     | Unit with fixture mediainfo output | Parse audio tracks, missing tracks, various codecs                  |
| `processors/tv.py`      | Unit with mocked SonarrClient      | Tagging logic: dub/semi-dub/wrong-dub, quick mode, genre filtering  |
| `processors/movies.py`  | Unit with mocked RadarrClient      | Same tagging logic for movies                                       |
| `storage/json_store.py` | Unit with temp files               | Load/save state, corruption handling                                |
| `__init__.py`           | Integration                        | Full `run()` with mocked APIs and real mediainfo                    |

**Mocking boundaries:**

- HTTP requests: mocked with `responses`
- File system: real temp directories (fast, isolated)
- mediainfo CLI: mocked output for unit tests, real binary for integration

## Example Test Patterns

**Mocking HTTP with responses (services/test_sonarr.py):**

```python
import responses
from taggarr.services.sonarr import SonarrClient

@responses.activate
def test_get_series_returns_all_shows():
    responses.add(
        responses.GET,
        "http://sonarr:8989/api/v3/series",
        json=[{"id": 1, "title": "Breaking Bad", "path": "/tv/breaking-bad"}],
    )

    client = SonarrClient(url="http://sonarr:8989", api_key="test-key")
    series = client.get_series()

    assert len(series) == 1
    assert series[0]["title"] == "Breaking Bad"
```

**Testing tagging logic (processors/test_tv.py):**

```python
def test_show_tagged_dub_when_all_episodes_have_target_language(mock_sonarr, mock_media):
    mock_media.get_audio_languages.return_value = ["en", "ja"]  # Has English dub

    result = process_show(show, target_languages=["en"], client=mock_sonarr)

    assert result.tag == "dub"

def test_show_tagged_semi_dub_when_some_episodes_missing_target(mock_sonarr, mock_media):
    # First episode has dub, second doesn't
    mock_media.get_audio_languages.side_effect = [["en", "ja"], ["ja"]]

    result = process_show(show, target_languages=["en"], client=mock_sonarr)

    assert result.tag == "semi-dub"
```

**Shared fixtures (conftest.py):**

```python
@pytest.fixture
def mock_sonarr(mocker):
    return mocker.Mock(spec=SonarrClient)

@pytest.fixture
def sample_config(tmp_path):
    config_file = tmp_path / "taggarr.yaml"
    config_file.write_text("instances:\n  sonarr:\n    type: sonarr\n    url: http://localhost:8989")
    return config_file
```

## Implementation Phases

### Phase 1: Infrastructure setup

- Create `pyproject.toml` with test dependencies
- Set up `tests/` directory structure and `conftest.py`
- Add GitHub Actions workflow
- Verify `pytest` runs (even with no tests yet)

### Phase 2: Pure functions first (easiest wins)

- `test_languages.py` - Language utilities
- `test_config_schema.py` - Dataclass validation
- `test_config_loader.py` - YAML parsing, env interpolation

### Phase 3: Service layer with HTTP mocking

- `test_sonarr.py` - All API methods, error cases
- `test_radarr.py` - Mirror Sonarr tests
- `test_media.py` - mediainfo output parsing

### Phase 4: Core business logic

- `test_tv.py` - TV processor with all tagging scenarios
- `test_movies.py` - Movie processor
- `test_nfo.py` - NFO read/write

### Phase 5: Storage and integration

- `test_json_store.py` - State persistence
- `test_smoke.py` - End-to-end integration test

### Phase 6: Gap filling

- Run `pytest --cov-report=html` to find uncovered lines
- Add edge case tests until 100%
