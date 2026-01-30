# Configuration Reference

## Config File Location

Taggarr searches for config in this order:

1. CLI-specified: `--config /path/to/config.yaml`
2. Working directory: `./taggarr.yaml`
3. User config: `~/.config/taggarr/config.yaml`
4. System config: `/etc/taggarr/config.yaml`

## YAML Structure

```yaml
defaults:
  target_languages: [en]
  tags:
    dub: "dub"
    semi: "semi-dub"
    wrong: "wrong-dub"
  dry_run: false
  quick_mode: false
  run_interval_seconds: 7200
  log_level: INFO
  log_path: /logs

instances:
  instance-name:
    type: sonarr | radarr
    url: http://host:port
    api_key: key-or-${ENV_VAR}
    root_path: /path/to/media
    # Optional overrides:
    target_languages: [ja, en]
    tags: { dub: "dubbed" }
    target_genre: Anime
    dry_run: true
    quick_mode: true
```

## Defaults Section

| Field                  | Type   | Default     | Description                        |
| ---------------------- | ------ | ----------- | ---------------------------------- |
| `target_languages`     | list   | `[en]`      | Languages to check for dubs        |
| `tags.dub`             | string | `dub`       | Tag for fully dubbed content       |
| `tags.semi`            | string | `semi-dub`  | Tag for partially dubbed content   |
| `tags.wrong`           | string | `wrong-dub` | Tag for unexpected languages       |
| `dry_run`              | bool   | `false`     | Preview mode without API writes    |
| `quick_mode`           | bool   | `false`     | Scan only first episode per season |
| `run_interval_seconds` | int    | `7200`      | Loop interval (2 hours)            |
| `log_level`            | string | `INFO`      | DEBUG, INFO, WARNING, ERROR        |
| `log_path`             | string | `/logs`     | Directory for log files            |

## Instance Section

| Field              | Required | Description                            |
| ------------------ | -------- | -------------------------------------- |
| `type`             | Yes      | `sonarr` or `radarr`                   |
| `url`              | Yes      | Base URL (e.g., `http://sonarr:8989`)  |
| `api_key`          | Yes      | API key (supports `${ENV_VAR}` syntax) |
| `root_path`        | Yes      | Path to media library root             |
| `target_languages` | No       | Override default languages             |
| `tags`             | No       | Override tag names (partial OK)        |
| `target_genre`     | No       | Filter to specific genre               |
| `dry_run`          | No       | Override default dry_run               |
| `quick_mode`       | No       | Override default quick_mode            |

## Environment Variable Interpolation

Use `${VAR_NAME}` in any string value to reference environment variables:

```yaml
instances:
  sonarr:
    api_key: ${SONARR_API_KEY}
    root_path: ${MEDIA_ROOT}/tv
```

Missing env vars cause a ConfigError with the variable name.

## CLI Options

```bash
python main.py                              # Process all instances
python main.py --config /path/to/config.yaml
python main.py --instances sonarr,radarr    # Process specific instances
python main.py --dry-run                    # Preview without writes
python main.py --quick                      # First episode only per season
python main.py --write-mode 0               # Normal (default)
python main.py --write-mode 1               # Rewrite all tags and JSON
python main.py --write-mode 2               # Remove all tags and JSON
python main.py --loop                       # Run continuously
```

## Example: Multi-Instance Setup

```yaml
defaults:
  target_languages: [en]

instances:
  sonarr:
    type: sonarr
    url: http://sonarr:8989
    api_key: ${SONARR_API_KEY}
    root_path: /tv

  sonarr-4k:
    type: sonarr
    url: http://sonarr-4k:8989
    api_key: ${SONARR_4K_API_KEY}
    root_path: /tv-4k

  sonarr-anime:
    type: sonarr
    url: http://sonarr-anime:8989
    api_key: ${SONARR_ANIME_API_KEY}
    root_path: /anime
    target_languages: [ja, en]
    target_genre: Anime

  radarr:
    type: radarr
    url: http://radarr:7878
    api_key: ${RADARR_API_KEY}
    root_path: /movies
```
