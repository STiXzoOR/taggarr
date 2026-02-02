# Testing Guidelines

## Requirements

- **Target:** 100% coverage for new code
- **Minimum:** 99% overall coverage must be maintained
- **Approach:** Write tests first (TDD) when possible

## Commands

```bash
./test.sh                                      # Run all tests
uv run pytest                                  # Alternative
uv run pytest --cov=taggarr --cov-fail-under=99  # With coverage check
uv run pytest tests/unit/test_config_loader.py -v  # Single file
```

## Test Structure

```
tests/
├── unit/
│   ├── test_config_loader.py
│   ├── test_languages.py
│   ├── test_nfo.py
│   ├── processors/
│   │   ├── test_tv.py
│   │   └── test_movies.py
│   ├── services/
│   │   ├── test_sonarr.py
│   │   ├── test_radarr.py
│   │   └── test_media.py
│   └── storage/
│       └── test_json_store.py
└── fixtures/
    ├── valid_config.yaml
    └── minimal_config.yaml
```

## Patterns

### Mocking External Services

```python
from unittest.mock import Mock, patch

def test_sonarr_client(mocker):
    mock_response = mocker.patch('requests.get')
    mock_response.return_value.json.return_value = {'series': []}
    # ...
```

### Mocking HTTP Requests

```python
import responses

@responses.activate
def test_api_call():
    responses.add(
        responses.GET,
        "http://sonarr:8989/api/v3/series",
        json=[{"id": 1, "title": "Test"}],
        status=200
    )
    # ...
```

### Using Fixtures

```python
def test_with_tmp_path(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text("instances: ...")
    # ...

def test_with_monkeypatch(monkeypatch):
    monkeypatch.setenv("API_KEY", "test-key")
    # ...
```
