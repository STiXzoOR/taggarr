# Multi-Instance Sonarr/Radarr Support

## Overview

Add support for multiple Sonarr and Radarr instances with a unified YAML configuration file, replacing the current single-instance environment variable approach.

## Configuration

### File Location

Config file is searched in order (first found wins):

1. CLI-specified: `--config /path/to/taggarr.yaml`
2. Working directory: `./taggarr.yaml`
3. User config: `~/.config/taggarr/config.yaml`
4. System config: `/etc/taggarr/config.yaml`

Missing config file results in a clear error listing searched locations.

### File Format

```yaml
defaults:
  target_languages: [en]
  tags:
    dub: "dub"
    semi: "semi-dub"
    wrong: "wrong-dub"
  dry_run: false
  quick_mode: false

instances:
  sonarr:
    type: sonarr
    url: http://sonarr:8989
    api_key: ${SONARR_API_KEY}
    root_path: /media/tv

  sonarr-4k:
    type: sonarr
    url: http://sonarr-4k:8989
    api_key: ${SONARR_4K_API_KEY}
    root_path: /media/tv-4k

  sonarr-anime:
    type: sonarr
    url: http://sonarr-anime:8989
    api_key: ${SONARR_ANIME_API_KEY}
    root_path: /media/anime
    target_languages: [ja, en] # override default

  radarr:
    type: radarr
    url: http://radarr:7878
    api_key: ${RADARR_API_KEY}
    root_path: /media/movies

  radarr-4k:
    type: radarr
    url: http://radarr-4k:7878
    api_key: ${RADARR_4K_API_KEY}
    root_path: /media/movies-4k
```

### Settings Hierarchy

Per-instance settings are merged with defaults (instance values win):

- `target_languages`: list of language codes
- `tags.dub`, `tags.semi`, `tags.wrong`: tag names
- `dry_run`: boolean
- `quick_mode`: boolean

### Environment Variable Interpolation

Config values support `${VAR}` syntax for environment variable expansion:

- Literal: `api_key: abc123`
- From env: `api_key: ${SONARR_API_KEY}`

Missing referenced env vars produce a clear error naming the variable.

## CLI Interface

```bash
# Run all instances (default)
python main.py

# Run specific instances
python main.py --instances sonarr,sonarr-anime

# Use specific config file
python main.py --config /path/to/taggarr.yaml

# Combine with existing flags
python main.py --instances radarr --dry-run
```

## Code Architecture

### Config Module (`taggarr/config.py`)

- `load_config(cli_path: str | None) -> Config`: Search for and load config file
- `Config` dataclass: `defaults: DefaultsConfig`, `instances: dict[str, InstanceConfig]`
- `InstanceConfig` dataclass: merged settings for a single instance
- Remove old env var loading

### Service Modules (`taggarr/services/sonarr.py`, `radarr.py`)

Convert from module-level globals to class-based clients:

```python
class SonarrClient:
    def __init__(self, url: str, api_key: str):
        self.url = url
        self.api_key = api_key

    def get_series_by_path(self, path: str) -> dict | None: ...
    def add_tag(self, series_id: int, tag: str, dry_run: bool = False): ...
    def remove_tag(self, series_id: int, tag: str, dry_run: bool = False): ...
    # ... other methods
```

Same pattern for `RadarrClient`.

### Processors (`taggarr/processors/tv.py`, `movies.py`)

- Accept `InstanceConfig` parameter instead of using globals
- Create appropriate service client based on instance type
- State file path derived from instance's `root_path` (unchanged)

### CLI (`main.py`)

- Add `--config` and `--instances` arguments via argparse
- Load config, filter instances if specified
- Run processors for each instance sequentially

## Runtime Flow

1. Parse CLI args
2. Load config file (search order or explicit path)
3. Validate config (required fields, valid URLs)
4. Filter instances if `--instances` specified
5. For each instance:
   - Log: `Processing instance: sonarr-anime (sonarr @ http://...)`
   - Create appropriate client (`SonarrClient` or `RadarrClient`)
   - Run processor with merged instance settings
   - State saved to `{root_path}/taggarr.json`
6. Exit 0 if all succeeded, 1 if any failed

## Error Handling

- Missing config file: list searched locations
- Invalid YAML: parse error with line number
- Missing required field: validation error naming the instance and field
- Missing env var: error naming the variable and config location
- Instance connection failure: log error, continue to next instance

## State Files

Each instance's `root_path` gets its own `taggarr.json` (current behavior, unchanged).

## Migration

Users create `taggarr.yaml` from existing env vars:

| Old Env Var        | New Config Location          |
| ------------------ | ---------------------------- |
| `SONARR_URL`       | `instances.<name>.url`       |
| `SONARR_API_KEY`   | `instances.<name>.api_key`   |
| `ROOT_TV_PATH`     | `instances.<name>.root_path` |
| `TARGET_LANGUAGES` | `defaults.target_languages`  |
| `TAG_DUB`          | `defaults.tags.dub`          |
| `TAG_SEMI`         | `defaults.tags.semi`         |
| `TAG_WRONG`        | `defaults.tags.wrong`        |
| `DRY_RUN`          | `defaults.dry_run`           |
| `QUICK_MODE`       | `defaults.quick_mode`        |

This is a clean break - env var fallback is not supported.
