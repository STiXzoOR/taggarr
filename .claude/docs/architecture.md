# Architecture & Data Flow

## Package Structure

```
taggarr/
├── __init__.py          # Entry point: run(), run_loop()
├── config_schema.py     # Dataclasses: Config, InstanceConfig, TagsConfig
├── config_loader.py     # YAML loader with ${VAR} env interpolation
├── logging_setup.py     # Logger configuration
├── nfo.py               # Kodi/Emby NFO file handling
├── languages.py         # Language code utilities and aliases
├── services/
│   ├── __init__.py      # Exports SonarrClient, RadarrClient
│   ├── sonarr.py        # SonarrClient class
│   ├── radarr.py        # RadarrClient class
│   └── media.py         # mediainfo audio track analysis
├── processors/
│   ├── __init__.py
│   ├── tv.py            # TV show scanning (process_all)
│   └── movies.py        # Movie scanning (process_all)
└── storage/
    ├── __init__.py
    └── json_store.py    # taggarr.json persistence
```

## Data Flow

```
main.py
    │
    ├─► load_config(cli_path)           # Parse YAML, expand ${VAR}
    │       └─► Config with instances
    │
    └─► taggarr.run(opts, config)
            │
            ├─► setup_logging(level, path)
            │
            └─► for each instance:
                    │
                    ├─► Create client (SonarrClient or RadarrClient)
                    │
                    ├─► json_store.load(root_path/taggarr.json)
                    │
                    ├─► processor.process_all(client, instance, opts, data)
                    │       │
                    │       ├─► Scan folders in root_path
                    │       ├─► media.analyze_audio() via mediainfo
                    │       ├─► Determine tag (dub/semi-dub/wrong-dub/none)
                    │       ├─► client.add_tag() / client.remove_tag()
                    │       └─► nfo.update_tag() if applicable
                    │
                    └─► json_store.save(root_path/taggarr.json)
```

## Key Classes

### SonarrClient / RadarrClient

Instance-based API clients that receive url and api_key in constructor:

```python
client = SonarrClient(url="http://sonarr:8989", api_key="abc123")
client.get_series_by_path("/tv/Show Name")
client.add_tag(series_id=123, tag="dub", dry_run=False)
```

### InstanceConfig

Per-instance configuration with merged defaults:

```python
@dataclass
class InstanceConfig:
    name: str                    # Instance identifier
    type: Literal["sonarr", "radarr"]
    url: str
    api_key: str
    root_path: str
    target_languages: List[str]  # Merged from defaults
    tags: TagsConfig             # Merged from defaults
    dry_run: bool
    quick_mode: bool
    target_genre: Optional[str]
```

## State Storage

Each instance root_path contains its own taggarr.json:

```
/media/tv/taggarr.json          # sonarr instance state
/media/tv-4k/taggarr.json       # sonarr-4k instance state
/media/movies/taggarr.json      # radarr instance state
```

State tracks: display_name, tag, last_scan, original_language, seasons/movies data, last_modified timestamps.

## Change Detection

Compares last_modified timestamps of season/movie folders against saved JSON to skip unchanged content.
