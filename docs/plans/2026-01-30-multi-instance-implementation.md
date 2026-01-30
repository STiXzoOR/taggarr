# Multi-Instance Support Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Support multiple Sonarr/Radarr instances via YAML configuration file.

**Architecture:** Replace env var config with YAML loader, convert services to class-based clients, inject instance config into processors.

**Tech Stack:** Python 3, PyYAML, dataclasses

---

## Task 1: Add PyYAML Dependency

**Files:**

- Create: `requirements.txt`

**Step 1: Create requirements.txt**

```
PyYAML>=6.0
python-dotenv>=1.0.0
requests>=2.28.0
```

**Step 2: Verify pip can parse it**

Run: `pip install --dry-run -r requirements.txt`
Expected: Shows packages would be installed (no errors)

**Step 3: Commit**

```bash
git add requirements.txt
git commit -m "chore: add requirements.txt with PyYAML dependency"
```

---

## Task 2: Create Config Data Classes

**Files:**

- Create: `taggarr/config_schema.py`

**Step 1: Write config schema**

```python
"""Configuration data classes."""

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class TagsConfig:
    """Tag name configuration."""
    dub: str = "dub"
    semi: str = "semi-dub"
    wrong: str = "wrong-dub"


@dataclass
class DefaultsConfig:
    """Default settings applied to all instances."""
    target_languages: list[str] = field(default_factory=lambda: ["en"])
    tags: TagsConfig = field(default_factory=TagsConfig)
    dry_run: bool = False
    quick_mode: bool = False
    run_interval_seconds: int = 7200
    log_level: str = "INFO"
    log_path: str = "/logs"


@dataclass
class InstanceConfig:
    """Configuration for a single Sonarr/Radarr instance."""
    name: str
    type: Literal["sonarr", "radarr"]
    url: str
    api_key: str
    root_path: str
    target_languages: list[str] = field(default_factory=list)
    tags: TagsConfig = field(default_factory=TagsConfig)
    dry_run: bool = False
    quick_mode: bool = False
    target_genre: str | None = None


@dataclass
class Config:
    """Top-level configuration."""
    defaults: DefaultsConfig
    instances: dict[str, InstanceConfig]
```

**Step 2: Verify syntax**

Run: `python -c "from taggarr.config_schema import Config; print('OK')"`
Expected: `OK`

**Step 3: Commit**

```bash
git add taggarr/config_schema.py
git commit -m "feat: add config data classes for multi-instance support"
```

---

## Task 3: Create YAML Config Loader

**Files:**

- Create: `taggarr/config_loader.py`

**Step 1: Write the loader**

```python
"""YAML configuration loader with env var interpolation."""

import os
import re
import yaml
from pathlib import Path

from taggarr.config_schema import (
    Config, DefaultsConfig, InstanceConfig, TagsConfig
)


class ConfigError(Exception):
    """Configuration loading error."""
    pass


def load_config(cli_path: str | None = None) -> Config:
    """Load configuration from YAML file.

    Search order:
    1. CLI-specified path
    2. ./taggarr.yaml
    3. ~/.config/taggarr/config.yaml
    4. /etc/taggarr/config.yaml
    """
    search_paths = [
        Path("./taggarr.yaml"),
        Path.home() / ".config" / "taggarr" / "config.yaml",
        Path("/etc/taggarr/config.yaml"),
    ]

    if cli_path:
        config_path = Path(cli_path)
        if not config_path.exists():
            raise ConfigError(f"Config file not found: {cli_path}")
    else:
        config_path = None
        for path in search_paths:
            if path.exists():
                config_path = path
                break

        if config_path is None:
            searched = "\n  ".join(str(p) for p in search_paths)
            raise ConfigError(
                f"No config file found. Searched:\n  {searched}\n\n"
                "Create taggarr.yaml or specify --config path"
            )

    return _parse_config(config_path)


def _parse_config(path: Path) -> Config:
    """Parse YAML config file."""
    try:
        with open(path) as f:
            raw = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigError(f"Invalid YAML in {path}: {e}")

    if not isinstance(raw, dict):
        raise ConfigError(f"Config must be a YAML mapping, got {type(raw).__name__}")

    # Parse defaults
    defaults_raw = raw.get("defaults", {})
    defaults = _parse_defaults(defaults_raw)

    # Parse instances
    instances_raw = raw.get("instances", {})
    if not instances_raw:
        raise ConfigError("No instances configured")

    instances = {}
    for name, inst_raw in instances_raw.items():
        instances[name] = _parse_instance(name, inst_raw, defaults)

    return Config(defaults=defaults, instances=instances)


def _parse_defaults(raw: dict) -> DefaultsConfig:
    """Parse defaults section."""
    tags_raw = raw.get("tags", {})
    tags = TagsConfig(
        dub=_interpolate(tags_raw.get("dub", "dub")),
        semi=_interpolate(tags_raw.get("semi", "semi-dub")),
        wrong=_interpolate(tags_raw.get("wrong", "wrong-dub")),
    )

    target_langs = raw.get("target_languages", ["en"])
    if isinstance(target_langs, str):
        target_langs = [lang.strip() for lang in target_langs.split(",")]

    return DefaultsConfig(
        target_languages=[_interpolate(lang) for lang in target_langs],
        tags=tags,
        dry_run=raw.get("dry_run", False),
        quick_mode=raw.get("quick_mode", False),
        run_interval_seconds=raw.get("run_interval_seconds", 7200),
        log_level=_interpolate(raw.get("log_level", "INFO")),
        log_path=_interpolate(raw.get("log_path", "/logs")),
    )


def _parse_instance(name: str, raw: dict, defaults: DefaultsConfig) -> InstanceConfig:
    """Parse a single instance, merging with defaults."""
    # Required fields
    for field in ["type", "url", "api_key", "root_path"]:
        if field not in raw:
            raise ConfigError(f"Instance '{name}' missing required field: {field}")

    inst_type = raw["type"]
    if inst_type not in ("sonarr", "radarr"):
        raise ConfigError(f"Instance '{name}' has invalid type: {inst_type}")

    # Tags: merge with defaults
    tags_raw = raw.get("tags", {})
    tags = TagsConfig(
        dub=_interpolate(tags_raw.get("dub", defaults.tags.dub)),
        semi=_interpolate(tags_raw.get("semi", defaults.tags.semi)),
        wrong=_interpolate(tags_raw.get("wrong", defaults.tags.wrong)),
    )

    # Target languages: use instance or default
    target_langs = raw.get("target_languages", defaults.target_languages)
    if isinstance(target_langs, str):
        target_langs = [lang.strip() for lang in target_langs.split(",")]

    return InstanceConfig(
        name=name,
        type=inst_type,
        url=_interpolate(raw["url"]).rstrip("/"),
        api_key=_interpolate(raw["api_key"]),
        root_path=_interpolate(raw["root_path"]),
        target_languages=[_interpolate(lang) for lang in target_langs],
        tags=tags,
        dry_run=raw.get("dry_run", defaults.dry_run),
        quick_mode=raw.get("quick_mode", defaults.quick_mode),
        target_genre=_interpolate(raw.get("target_genre")) if raw.get("target_genre") else None,
    )


def _interpolate(value: str | None) -> str | None:
    """Expand ${VAR} references in a string value."""
    if value is None:
        return None
    if not isinstance(value, str):
        return value

    pattern = re.compile(r'\$\{([^}]+)\}')

    def replacer(match):
        var_name = match.group(1)
        env_value = os.environ.get(var_name)
        if env_value is None:
            raise ConfigError(f"Environment variable not set: {var_name}")
        return env_value

    return pattern.sub(replacer, value)
```

**Step 2: Verify syntax**

Run: `python -c "from taggarr.config_loader import load_config; print('OK')"`
Expected: `OK`

**Step 3: Commit**

```bash
git add taggarr/config_loader.py
git commit -m "feat: add YAML config loader with env var interpolation"
```

---

## Task 4: Create SonarrClient Class

**Files:**

- Modify: `taggarr/services/sonarr.py`

**Step 1: Rewrite as class-based client**

Replace entire file with:

```python
"""Sonarr API client."""

import os
import time
import logging

import requests

logger = logging.getLogger("taggarr")


class SonarrClient:
    """Client for Sonarr API."""

    def __init__(self, url: str, api_key: str):
        self.url = url.rstrip("/")
        self.api_key = api_key
        self._headers = {"X-Api-Key": self.api_key}

    def get_series_by_path(self, path: str) -> dict | None:
        """Find series by folder path."""
        try:
            resp = requests.get(
                f"{self.url}/api/v3/series",
                headers=self._headers
            )
            for s in resp.json():
                if os.path.basename(s['path']) == os.path.basename(path):
                    return s
        except Exception as e:
            logger.warning(f"Sonarr lookup failed: {e}")
        return None

    def get_series_id(self, path: str) -> int | None:
        """Get just the series ID."""
        series = self.get_series_by_path(path)
        return series['id'] if series else None

    def add_tag(self, series_id: int, tag: str, dry_run: bool = False) -> None:
        """Add a tag to a series."""
        if dry_run:
            logger.info(f"[Dry Run] Would add tag '{tag}' to series {series_id}")
            return
        tag_id = self._get_or_create_tag(tag)
        self._modify_series_tags(series_id, tag_id, remove=False)

    def remove_tag(self, series_id: int, tag: str, dry_run: bool = False) -> None:
        """Remove a tag from a series."""
        if dry_run:
            logger.info(f"[Dry Run] Would remove tag '{tag}' from series {series_id}")
            return
        tag_id = self._get_tag_id(tag)
        if tag_id:
            self._modify_series_tags(series_id, tag_id, remove=True)

    def refresh_series(self, series_id: int, dry_run: bool = False) -> None:
        """Trigger a series refresh in Sonarr."""
        if dry_run:
            logger.info(f"[Dry Run] Would trigger refresh for series {series_id}")
            return
        try:
            url = f"{self.url}/api/v3/command"
            payload = {"name": "RefreshSeries", "seriesId": series_id}
            requests.post(url, json=payload, headers=self._headers, timeout=10)
            logger.debug(f"Sonarr refresh triggered for series ID: {series_id}")
        except Exception as e:
            logger.warning(f"Failed to trigger Sonarr refresh: {e}")

    def _get_tag_id(self, tag: str) -> int | None:
        """Get tag ID by label."""
        try:
            r = requests.get(
                f"{self.url}/api/v3/tag",
                headers=self._headers
            )
            for t in r.json():
                if t["label"].lower() == tag.lower():
                    return t["id"]
        except Exception:
            pass
        return None

    def _get_or_create_tag(self, tag: str) -> int:
        """Get existing tag ID or create new one."""
        tag_id = self._get_tag_id(tag)
        if tag_id is None:
            r = requests.post(
                f"{self.url}/api/v3/tag",
                headers=self._headers,
                json={"label": tag}
            )
            tag_id = r.json()["id"]
            logger.debug(f"Created new Sonarr tag '{tag}' with ID {tag_id}")
        return tag_id

    def _modify_series_tags(self, series_id: int, tag_id: int, remove: bool = False) -> None:
        """Add or remove a tag from series."""
        try:
            s_url = f"{self.url}/api/v3/series/{series_id}"
            s_data = requests.get(s_url, headers=self._headers).json()

            if remove and tag_id in s_data["tags"]:
                s_data["tags"].remove(tag_id)
                logger.debug(f"Removing tag ID {tag_id} from series {series_id}")
            elif not remove and tag_id not in s_data["tags"]:
                s_data["tags"].append(tag_id)
                logger.debug(f"Adding tag ID {tag_id} to series {series_id}")

            requests.put(s_url, headers=self._headers, json=s_data)
            time.sleep(0.5)
        except Exception as e:
            logger.warning(f"Failed to modify series tags: {e}")
```

**Step 2: Verify syntax**

Run: `python -c "from taggarr.services.sonarr import SonarrClient; print('OK')"`
Expected: `OK`

**Step 3: Commit**

```bash
git add taggarr/services/sonarr.py
git commit -m "refactor: convert sonarr module to class-based SonarrClient"
```

---

## Task 5: Create RadarrClient Class

**Files:**

- Modify: `taggarr/services/radarr.py`

**Step 1: Rewrite as class-based client**

Replace entire file with:

```python
"""Radarr API client."""

import os
import time
import logging

import requests

logger = logging.getLogger("taggarr")


class RadarrClient:
    """Client for Radarr API."""

    def __init__(self, url: str, api_key: str):
        self.url = url.rstrip("/")
        self.api_key = api_key
        self._headers = {"X-Api-Key": self.api_key}

    def get_movies(self) -> list[dict]:
        """Fetch all movies from Radarr API."""
        try:
            resp = requests.get(
                f"{self.url}/api/v3/movie",
                headers=self._headers
            )
            return resp.json()
        except Exception as e:
            logger.warning(f"Failed to fetch Radarr movies: {e}")
            return []

    def get_movie_by_path(self, path: str) -> dict | None:
        """Find a specific movie by its folder path."""
        try:
            resp = requests.get(
                f"{self.url}/api/v3/movie",
                headers=self._headers
            )
            for m in resp.json():
                if os.path.basename(m['path']) == os.path.basename(path):
                    return m
        except Exception as e:
            logger.warning(f"Radarr lookup failed: {e}")
        return None

    def add_tag(self, movie_id: int, tag: str, dry_run: bool = False) -> None:
        """Add a tag to a movie."""
        if dry_run:
            logger.info(f"[Dry Run] Would add tag '{tag}' to movie {movie_id}")
            return
        tag_id = self._get_or_create_tag(tag)
        self._modify_movie_tags(movie_id, tag_id, remove=False)

    def remove_tag(self, movie_id: int, tag: str, dry_run: bool = False) -> None:
        """Remove a tag from a movie."""
        if dry_run:
            logger.info(f"[Dry Run] Would remove tag '{tag}' from movie {movie_id}")
            return
        tag_id = self._get_tag_id(tag)
        if tag_id:
            self._modify_movie_tags(movie_id, tag_id, remove=True)

    def _get_tag_id(self, tag: str) -> int | None:
        """Get tag ID by label."""
        try:
            r = requests.get(
                f"{self.url}/api/v3/tag",
                headers=self._headers
            )
            for t in r.json():
                if t["label"].lower() == tag.lower():
                    return t["id"]
        except Exception:
            pass
        return None

    def _get_or_create_tag(self, tag: str) -> int:
        """Get existing tag ID or create new one."""
        tag_id = self._get_tag_id(tag)
        if tag_id is None:
            r = requests.post(
                f"{self.url}/api/v3/tag",
                headers=self._headers,
                json={"label": tag}
            )
            tag_id = r.json()["id"]
            logger.debug(f"Created new Radarr tag '{tag}' with ID {tag_id}")
        return tag_id

    def _modify_movie_tags(self, movie_id: int, tag_id: int, remove: bool = False) -> None:
        """Add or remove a tag from movie."""
        try:
            m_url = f"{self.url}/api/v3/movie/{movie_id}"
            m_data = requests.get(m_url, headers=self._headers).json()

            if remove and tag_id in m_data["tags"]:
                m_data["tags"].remove(tag_id)
                logger.debug(f"Removing tag ID {tag_id} from movie {movie_id}")
            elif not remove and tag_id not in m_data["tags"]:
                m_data["tags"].append(tag_id)
                logger.debug(f"Adding tag ID {tag_id} to movie {movie_id}")

            requests.put(m_url, headers=self._headers, json=m_data)
            time.sleep(0.5)
        except Exception as e:
            logger.warning(f"Failed to modify movie tags: {e}")
```

**Step 2: Verify syntax**

Run: `python -c "from taggarr.services.radarr import RadarrClient; print('OK')"`
Expected: `OK`

**Step 3: Commit**

```bash
git add taggarr/services/radarr.py
git commit -m "refactor: convert radarr module to class-based RadarrClient"
```

---

## Task 6: Refactor TV Processor for Instance Config

**Files:**

- Modify: `taggarr/processors/tv.py`

**Step 1: Rewrite to accept InstanceConfig**

Replace entire file with:

```python
"""TV show scanning and tagging processor."""

import os
import re
import logging
from datetime import datetime

from taggarr.config_schema import InstanceConfig
from taggarr.services.sonarr import SonarrClient
from taggarr.services import media
from taggarr import nfo, languages

logger = logging.getLogger("taggarr")


def process_all(client: SonarrClient, instance: InstanceConfig, opts, taggarr_data: dict) -> dict:
    """Process all TV shows for a Sonarr instance."""
    quick = opts.quick or instance.quick_mode
    dry_run = opts.dry_run or instance.dry_run
    write_mode = opts.write_mode

    language_codes = languages.build_language_codes(instance.target_languages)

    for show_folder in sorted(os.listdir(instance.root_path)):
        show_path = os.path.abspath(os.path.join(instance.root_path, show_folder))
        if not os.path.isdir(show_path):
            continue

        saved_data = taggarr_data["series"].get(show_path, {})
        saved_seasons = saved_data.get("seasons", {})

        # Check if scan needed
        is_new = show_path not in taggarr_data["series"]
        changed = _has_changes(show_path, saved_seasons)
        new_seasons = _has_new_seasons(show_path, saved_seasons)

        if write_mode == 0 and not (changed or is_new or new_seasons):
            logger.info(f"Skipping {show_folder} - no new or updated seasons")
            continue

        # Genre filter via NFO
        nfo_path = os.path.join(show_path, "tvshow.nfo")
        if not os.path.exists(nfo_path):
            logger.debug(f"No NFO found for: {show_folder}")
            continue

        if not _passes_genre_filter(nfo_path, instance.target_genre):
            logger.info(f"Skipping {show_folder}: genre mismatch")
            continue

        logger.info(f"Processing show: {show_folder}")

        # Get Sonarr metadata
        series = client.get_series_by_path(show_path)
        if not series:
            logger.warning(f"No Sonarr metadata for {show_folder}")
            continue

        series_id = series['id']

        # Handle remove mode
        if write_mode == 2:
            logger.info(f"Removing tags for {show_folder}")
            for tag in [instance.tags.dub, instance.tags.semi, instance.tags.wrong]:
                client.remove_tag(series_id, tag, dry_run)
            if show_path in taggarr_data["series"]:
                del taggarr_data["series"][show_path]
            continue

        # Scan and determine tag
        tag, seasons = _scan_show(
            show_path, series, instance, language_codes, quick
        )
        logger.info(f"Tagged as {tag or 'no tag (original)'}")

        # Apply tags to Sonarr
        _apply_tags(client, series_id, tag, instance, dry_run)

        # Update NFO tag
        if tag in [instance.tags.dub, instance.tags.semi, instance.tags.wrong]:
            nfo.update_tag(nfo_path, tag, dry_run)

        # Get current mtime for storage
        current_mtime = 0
        for d in os.listdir(show_path):
            season_path = os.path.join(show_path, d)
            if os.path.isdir(season_path) and d.lower().startswith("season"):
                current_mtime = max(current_mtime, os.path.getmtime(season_path))

        # Save state
        taggarr_data["series"][show_path] = _build_entry(
            show_folder, tag, seasons, series, current_mtime
        )

        # Refresh if in rewrite mode
        if write_mode == 1:
            client.refresh_series(series_id, dry_run)

    return taggarr_data


def _scan_show(show_path: str, series_meta: dict, instance: InstanceConfig,
               language_codes: set, quick: bool = False) -> tuple[str | None, dict]:
    """Scan all seasons and determine overall tag."""
    seasons = {}
    has_wrong, has_dub = False, False

    for entry in sorted(os.listdir(show_path)):
        season_path = os.path.join(show_path, entry)
        if not (os.path.isdir(season_path) and entry.lower().startswith("season")):
            continue

        logger.info(f"Scanning season: {entry}")
        stats = _scan_season(season_path, series_meta, instance, language_codes, quick)
        stats["last_modified"] = os.path.getmtime(season_path)
        stats["status"] = _determine_status(stats)

        has_wrong = has_wrong or bool(stats["unexpected_languages"])
        has_dub = has_dub or bool(stats["dub"])
        seasons[entry] = stats

    # Determine final tag
    statuses = [s["status"] for s in seasons.values()]
    if has_wrong:
        return instance.tags.wrong, seasons
    elif all(s == "fully-dub" for s in statuses):
        return instance.tags.dub, seasons
    elif any(s in ("fully-dub", "semi-dub") for s in statuses):
        return instance.tags.semi, seasons

    return None, seasons


def _scan_season(season_path: str, series_meta: dict, instance: InstanceConfig,
                 language_codes: set, quick: bool = False) -> dict:
    """Scan episodes in a season folder."""
    video_exts = ['.mkv', '.mp4', '.m4v', '.avi', '.webm', '.mov', '.mxf']
    files = sorted([
        f for f in os.listdir(season_path)
        if os.path.splitext(f)[1].lower() in video_exts
    ])
    if quick and files:
        files = [files[0]]

    # Get original language codes
    original_lang = series_meta.get("originalLanguage", "")
    if isinstance(original_lang, dict):
        original_lang_name = original_lang.get("name", "").lower()
    else:
        original_lang_name = str(original_lang).lower()

    original_codes = languages.get_aliases(original_lang_name)

    stats = {
        "episodes": len(files) if not quick else 1,
        "original_dub": [],
        "dub": [],
        "missing_dub": [],
        "unexpected_languages": [],
    }

    for f in files:
        full_path = os.path.join(season_path, f)
        langs = media.analyze_audio(full_path)

        match = re.search(r'(E\d{2})', f, re.IGNORECASE)
        ep_name = match.group(1) if match else os.path.splitext(f)[0]

        # Handle fallback audio track
        if "__fallback_original__" in langs:
            stats["original_dub"].append(ep_name)
            logger.info(f"Audio track not labelled for {ep_name} — assuming original language")
            continue

        langs_set = set(langs)
        has_target = langs_set.intersection(language_codes)

        # Build aliases for detected languages
        langs_aliases = set()
        for lang in langs:
            langs_aliases.update(languages.get_aliases(lang))

        # Check for missing target languages
        missing_target = set()
        for t in instance.target_languages:
            t_aliases = languages.get_aliases(t)
            if not langs_aliases.intersection(t_aliases):
                missing_target.add(t)

        has_original = langs_set.intersection(original_codes)

        if has_original:
            stats["original_dub"].append(ep_name)
        if has_target:
            stats["dub"].append(f"{ep_name}:{', '.join(sorted(has_target))}")
        if missing_target:
            short_missing = [languages.get_primary_code(m) for m in sorted(missing_target)]
            stats["missing_dub"].append(f"{ep_name}:{', '.join(short_missing)}")

        # Collect unexpected languages
        for lang in langs:
            if lang not in language_codes and lang not in original_codes:
                stats["unexpected_languages"].append(lang)

    stats["unexpected_languages"] = sorted(set(stats["unexpected_languages"]))
    return stats


def _has_changes(show_path: str, saved_seasons: dict) -> bool:
    """Check if any season has been modified."""
    for d in os.listdir(show_path):
        season_path = os.path.join(show_path, d)
        if os.path.isdir(season_path) and d.lower().startswith("season"):
            current_mtime = os.path.getmtime(season_path)
            saved_mtime = saved_seasons.get(d, {}).get("last_modified", 0)
            if current_mtime > saved_mtime:
                return True
    return False


def _has_new_seasons(show_path: str, saved_seasons: dict) -> bool:
    """Check if there are new season folders."""
    existing = set(saved_seasons.keys())
    current = set(
        d for d in os.listdir(show_path)
        if os.path.isdir(os.path.join(show_path, d)) and d.lower().startswith("season")
    )
    return len(current - existing) > 0


def _passes_genre_filter(nfo_path: str, target_genre: str | None) -> bool:
    """Check if show passes genre filter."""
    if not target_genre:
        return True
    genres = nfo.get_genres(nfo_path)
    return target_genre.lower() in genres


def _apply_tags(client: SonarrClient, series_id: int, tag: str | None,
                instance: InstanceConfig, dry_run: bool) -> None:
    """Apply appropriate tags and remove conflicting ones."""
    if tag:
        client.add_tag(series_id, tag, dry_run)
        if tag == instance.tags.wrong:
            client.remove_tag(series_id, instance.tags.semi, dry_run)
            client.remove_tag(series_id, instance.tags.dub, dry_run)
        elif tag == instance.tags.semi:
            client.remove_tag(series_id, instance.tags.wrong, dry_run)
            client.remove_tag(series_id, instance.tags.dub, dry_run)
        elif tag == instance.tags.dub:
            client.remove_tag(series_id, instance.tags.wrong, dry_run)
            client.remove_tag(series_id, instance.tags.semi, dry_run)
    else:
        logger.info("Removing all tags since it's original (no tag)")
        for t in [instance.tags.dub, instance.tags.semi, instance.tags.wrong]:
            client.remove_tag(series_id, t, dry_run)


def _determine_status(stats: dict) -> str:
    """Determine season status from stats."""
    if stats["unexpected_languages"]:
        return "wrong-dub"
    elif not stats["missing_dub"] and stats["dub"]:
        return "fully-dub"
    elif stats["dub"]:
        return "semi-dub"
    return "original"


def _build_entry(show_folder: str, tag: str | None, seasons: dict,
                 series: dict, mtime: float) -> dict:
    """Build taggarr.json entry for a show."""
    original_lang = series.get("originalLanguage", "")
    if isinstance(original_lang, dict):
        original_lang = original_lang.get("name", "").lower()
    else:
        original_lang = str(original_lang).lower()

    return {
        "display_name": show_folder,
        "tag": tag or "none",
        "last_scan": datetime.utcnow().isoformat() + "Z",
        "original_language": original_lang,
        "seasons": seasons,
        "last_modified": mtime,
    }
```

**Step 2: Verify syntax**

Run: `python -c "from taggarr.processors.tv import process_all; print('OK')"`
Expected: `OK`

**Step 3: Commit**

```bash
git add taggarr/processors/tv.py
git commit -m "refactor: update TV processor to accept InstanceConfig"
```

---

## Task 7: Refactor Movies Processor for Instance Config

**Files:**

- Modify: `taggarr/processors/movies.py`

**Step 1: Rewrite to accept InstanceConfig**

Replace entire file with:

```python
"""Movie scanning and tagging processor."""

import os
import logging
from datetime import datetime

from taggarr.config_schema import InstanceConfig
from taggarr.services.radarr import RadarrClient
from taggarr.services import media
from taggarr import nfo, languages

logger = logging.getLogger("taggarr")


def process_all(client: RadarrClient, instance: InstanceConfig, opts, taggarr_movies: dict) -> dict:
    """Process all movies for a Radarr instance."""
    quick = opts.quick or instance.quick_mode
    dry_run = opts.dry_run or instance.dry_run
    write_mode = opts.write_mode

    language_codes = languages.build_language_codes(instance.target_languages)

    logger.info("Starting movie scan...")

    for movie_folder in sorted(os.listdir(instance.root_path)):
        movie_path = os.path.abspath(os.path.join(instance.root_path, movie_folder))
        if not os.path.isdir(movie_path):
            continue

        # Skip non-movie items
        if movie_folder.startswith('.') or movie_folder.endswith('.json'):
            continue

        saved = taggarr_movies["movies"].get(movie_path, {})
        saved_mtime = saved.get("last_modified", 0)

        # Get current mtime
        try:
            current_mtime = max(
                os.path.getmtime(os.path.join(root, f))
                for root, dirs, files in os.walk(movie_path)
                for f in files if f.endswith(('.mkv', '.mp4', '.m4v', '.avi'))
            )
        except ValueError:
            current_mtime = 0

        is_new = movie_path not in taggarr_movies["movies"]
        changed = current_mtime > saved_mtime

        if write_mode == 0 and not (changed or is_new):
            logger.info(f"Skipping {movie_folder} - no changes")
            continue

        # Get Radarr metadata
        movie_meta = client.get_movie_by_path(movie_path)
        if not movie_meta:
            logger.warning(f"No Radarr metadata for {movie_folder}")
            continue

        # Skip movies not yet downloaded
        if not movie_meta.get("hasFile", False):
            logger.debug(f"Skipping {movie_folder} - not yet downloaded")
            continue

        # Genre filter
        if instance.target_genre:
            genres = [g.lower() for g in movie_meta.get("genres", [])]
            if instance.target_genre.lower() not in genres:
                logger.info(f"Skipping {movie_folder}: genre mismatch")
                continue

        logger.info(f"Processing movie: {movie_folder}")

        movie_id = movie_meta.get("id")
        if not movie_id:
            logger.warning(f"No Radarr ID for {movie_folder}")
            continue

        # Handle remove mode
        if write_mode == 2:
            logger.info(f"Removing tags for {movie_folder}")
            for tag in [instance.tags.dub, instance.tags.wrong]:
                client.remove_tag(movie_id, tag, dry_run)
            if movie_path in taggarr_movies["movies"]:
                del taggarr_movies["movies"][movie_path]
            continue

        # Scan movie
        scan_result = _scan_movie(movie_path, movie_meta, instance, language_codes)
        if scan_result is None:
            continue

        # Determine tag
        tag = _determine_tag(scan_result, instance, language_codes)
        logger.info(f"Tagged as {tag or 'no tag (original)'}")

        # Apply tags to Radarr
        if tag:
            client.add_tag(movie_id, tag, dry_run)
            if tag == instance.tags.wrong:
                client.remove_tag(movie_id, instance.tags.dub, dry_run)
            elif tag == instance.tags.dub:
                client.remove_tag(movie_id, instance.tags.wrong, dry_run)
        else:
            for t in [instance.tags.dub, instance.tags.wrong]:
                client.remove_tag(movie_id, t, dry_run)

        # Update NFO if applicable
        nfo_path = _find_nfo(movie_path, movie_folder)
        if nfo_path and tag in [instance.tags.dub, instance.tags.wrong]:
            nfo.update_movie_tag(nfo_path, tag, dry_run)

        # Save state
        taggarr_movies["movies"][movie_path] = {
            "display_name": movie_folder,
            "tag": tag or "none",
            "last_scan": datetime.utcnow().isoformat() + "Z",
            "original_language": scan_result["original_language"],
            "languages": scan_result["languages"],
            "last_modified": current_mtime,
        }

    return taggarr_movies


def _scan_movie(movie_path: str, movie_meta: dict, instance: InstanceConfig,
                language_codes: set) -> dict | None:
    """Scan a movie folder and return language analysis."""
    video_exts = ['.mkv', '.mp4', '.m4v', '.avi', '.webm', '.mov', '.mxf']
    ignore_patterns = ['-sample', 'sample.', 'extras', 'featurettes', 'behind the scenes', 'deleted scenes']

    # Find all video files
    video_files = []
    for root, dirs, files in os.walk(movie_path):
        dirs[:] = [d for d in dirs if not any(p in d.lower() for p in ignore_patterns)]
        for f in files:
            if os.path.splitext(f)[1].lower() in video_exts:
                if any(p in f.lower() for p in ignore_patterns):
                    continue
                full_path = os.path.join(root, f)
                video_files.append((full_path, os.path.getsize(full_path)))

    if not video_files:
        logger.warning(f"No video files found in {movie_path}")
        return None

    # Get largest file (main feature)
    main_file = max(video_files, key=lambda x: x[1])[0]
    logger.debug(f"Scanning main movie file: {os.path.basename(main_file)}")

    langs = media.analyze_audio(main_file)

    # Get original language
    original_lang = movie_meta.get("originalLanguage", {})
    if isinstance(original_lang, dict):
        original_lang_name = original_lang.get("name", "").lower()
    else:
        original_lang_name = str(original_lang).lower()

    original_codes = languages.get_aliases(original_lang_name)

    return {
        "file": os.path.basename(main_file),
        "languages": langs,
        "original_language": original_lang_name,
        "original_codes": original_codes,
        "last_modified": os.path.getmtime(main_file),
    }


def _determine_tag(scan_result: dict, instance: InstanceConfig,
                   language_codes: set) -> str | None:
    """Determine the appropriate tag for a movie."""
    if scan_result is None:
        return None

    langs = set(scan_result["languages"])
    original_codes = scan_result["original_codes"]

    # Handle fallback
    if "__fallback_original__" in langs:
        logger.info("Audio track not labelled — assuming original language")
        return None

    # Build aliases
    langs_aliases = set()
    for lang in langs:
        langs_aliases.update(languages.get_aliases(lang))

    # Check for all target languages
    has_all_targets = True
    for target in instance.target_languages:
        target_aliases = languages.get_aliases(target)
        if not langs_aliases.intersection(target_aliases):
            has_all_targets = False
            break

    # Check for unexpected languages
    unexpected = []
    for lang in langs:
        if lang not in language_codes and lang not in original_codes:
            unexpected.append(lang)

    if unexpected:
        return instance.tags.wrong
    elif has_all_targets:
        return instance.tags.dub

    return None


def _find_nfo(movie_path: str, movie_folder: str) -> str | None:
    """Find the movie's NFO file."""
    for pattern in ['movie.nfo', f"{movie_folder}.nfo"]:
        potential = os.path.join(movie_path, pattern)
        if os.path.exists(potential):
            return potential
    return None
```

**Step 2: Verify syntax**

Run: `python -c "from taggarr.processors.movies import process_all; print('OK')"`
Expected: `OK`

**Step 3: Commit**

```bash
git add taggarr/processors/movies.py
git commit -m "refactor: update movies processor to accept InstanceConfig"
```

---

## Task 8: Update Package Init for Multi-Instance

**Files:**

- Modify: `taggarr/__init__.py`

**Step 1: Rewrite to use new config and iterate instances**

Replace entire file with:

```python
"""Taggarr - Dub Analysis & Tagging."""

__description__ = "Dub Analysis & Tagging."
__author__ = "BASSHOUS3"
__version__ = "0.7.0"

import os
import time
import logging

from taggarr.config_loader import load_config, ConfigError
from taggarr.config_schema import Config, InstanceConfig
from taggarr.logging_setup import setup_logging
from taggarr.storage import json_store
from taggarr.processors import tv, movies
from taggarr.services.sonarr import SonarrClient
from taggarr.services.radarr import RadarrClient

_logger = None


def run(opts, config: Config):
    """Run a single scan cycle for all configured instances."""
    global _logger
    if _logger is None:
        _logger = setup_logging(
            level=config.defaults.log_level,
            path=config.defaults.log_path
        )

    _logger.info(f"Taggarr - {__description__}")
    _logger.info(f"Taggarr - v{__version__} started.")
    _logger.info("Starting Taggarr scan...")

    # Filter instances if specified
    instance_filter = getattr(opts, 'instances', None)
    if instance_filter:
        instance_names = [n.strip() for n in instance_filter.split(",")]
        instances = {k: v for k, v in config.instances.items() if k in instance_names}
        if not instances:
            _logger.error(f"No matching instances found for: {instance_filter}")
            return
    else:
        instances = config.instances

    # Log mode info
    if opts.quick:
        _logger.info("Quick mode: Scanning only first episode per season.")
    if opts.dry_run:
        _logger.info("Dry run mode: No API calls or file edits.")
    if opts.write_mode == 0:
        _logger.info("Write mode 0: Processing as usual.")
    elif opts.write_mode == 1:
        _logger.info("Rewrite mode: Everything will be rebuilt.")
    elif opts.write_mode == 2:
        _logger.info("Remove mode: Everything will be removed.")

    # Process each instance
    for name, instance in instances.items():
        _logger.info(f"Processing instance: {name} ({instance.type} @ {instance.url})")

        try:
            _process_instance(instance, opts)
        except Exception as e:
            _logger.error(f"Failed to process instance {name}: {e}")
            continue

    _logger.info("Finished Taggarr scan.")
    _logger.info(f"Next scan in {config.defaults.run_interval_seconds / 3600} hours.")


def _process_instance(instance: InstanceConfig, opts) -> None:
    """Process a single Sonarr/Radarr instance."""
    global _logger

    json_path = os.path.join(instance.root_path, "taggarr.json")

    if instance.type == "sonarr":
        client = SonarrClient(instance.url, instance.api_key)
        taggarr_data = json_store.load(json_path, key="series")
        taggarr_data = tv.process_all(client, instance, opts, taggarr_data)
        json_store.save(json_path, taggarr_data, key="series")

    elif instance.type == "radarr":
        client = RadarrClient(instance.url, instance.api_key)
        taggarr_data = json_store.load(json_path, key="movies")
        taggarr_data = movies.process_all(client, instance, opts, taggarr_data)
        json_store.save(json_path, taggarr_data, key="movies")


def run_loop(opts, config: Config):
    """Run scans continuously at configured interval."""
    while True:
        run(opts, config)
        time.sleep(config.defaults.run_interval_seconds)
```

**Step 2: Verify syntax**

Run: `python -c "from taggarr import run; print('OK')"`
Expected: `OK`

**Step 3: Commit**

```bash
git add taggarr/__init__.py
git commit -m "refactor: update package init for multi-instance processing"
```

---

## Task 9: Update Logging Setup for Config

**Files:**

- Modify: `taggarr/logging_setup.py`

**Step 1: Read current file**

Run: `cat taggarr/logging_setup.py`

**Step 2: Update to accept parameters**

Update the `setup_logging` function signature to accept `level` and `path` parameters instead of reading from config globals. Keep backward compatibility with defaults.

**Step 3: Verify syntax**

Run: `python -c "from taggarr.logging_setup import setup_logging; print('OK')"`
Expected: `OK`

**Step 4: Commit**

```bash
git add taggarr/logging_setup.py
git commit -m "refactor: update logging setup to accept config parameters"
```

---

## Task 10: Update CLI for Multi-Instance

**Files:**

- Modify: `main.py`

**Step 1: Rewrite CLI with new arguments**

Replace entire file with:

```python
#!/usr/bin/env python3
"""Taggarr - Dub Analysis & Tagging CLI."""

import argparse
import sys
import time

import taggarr
from taggarr.config_loader import load_config, ConfigError


def main():
    parser = argparse.ArgumentParser(description=taggarr.__description__)
    parser.add_argument(
        '--config', '-c',
        help="Path to config file (default: searches standard locations)"
    )
    parser.add_argument(
        '--instances', '-i',
        help="Comma-separated list of instances to process (default: all)"
    )
    parser.add_argument(
        '--write-mode', type=int, choices=[0, 1, 2],
        default=0,
        help="0=default, 1=rewrite all, 2=remove all"
    )
    parser.add_argument(
        '--quick', action='store_true',
        help="Scan only first episode per season"
    )
    parser.add_argument(
        '--dry-run', action='store_true',
        help="No API calls or file edits"
    )
    parser.add_argument(
        '--loop', action='store_true',
        help="Run continuously at configured interval"
    )
    opts = parser.parse_args()

    # Load configuration
    try:
        config = load_config(opts.config)
    except ConfigError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)

    # Run
    if opts.loop:
        taggarr.run_loop(opts, config)
    else:
        taggarr.run(opts, config)


if __name__ == '__main__':
    main()
```

**Step 2: Verify syntax**

Run: `python main.py --help`
Expected: Shows help with --config, --instances, --loop options

**Step 3: Commit**

```bash
git add main.py
git commit -m "feat: update CLI with --config and --instances arguments"
```

---

## Task 11: Delete Old Config Module

**Files:**

- Delete: `taggarr/config.py`

**Step 1: Remove old config**

```bash
rm taggarr/config.py
```

**Step 2: Commit**

```bash
git add -A
git commit -m "chore: remove deprecated env var config module"
```

---

## Task 12: Create Example Config File

**Files:**

- Create: `taggarr.example.yaml`

**Step 1: Create example config**

```yaml
# Taggarr Configuration
# Copy to taggarr.yaml and customize for your setup

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
  # Standard TV library
  sonarr:
    type: sonarr
    url: http://localhost:8989
    api_key: ${SONARR_API_KEY}
    root_path: /media/tv

  # 4K TV library
  sonarr-4k:
    type: sonarr
    url: http://localhost:8990
    api_key: ${SONARR_4K_API_KEY}
    root_path: /media/tv-4k

  # Anime library with Japanese + English targets
  sonarr-anime:
    type: sonarr
    url: http://localhost:8991
    api_key: ${SONARR_ANIME_API_KEY}
    root_path: /media/anime
    target_languages: [ja, en]
    tags:
      dub: "dubbed"

  # Standard movie library
  radarr:
    type: radarr
    url: http://localhost:7878
    api_key: ${RADARR_API_KEY}
    root_path: /media/movies

  # 4K movie library
  radarr-4k:
    type: radarr
    url: http://localhost:7879
    api_key: ${RADARR_4K_API_KEY}
    root_path: /media/movies-4k
```

**Step 2: Commit**

```bash
git add taggarr.example.yaml
git commit -m "docs: add example configuration file"
```

---

## Task 13: Update Services **init**.py

**Files:**

- Modify: `taggarr/services/__init__.py`

**Step 1: Read current file**

Run: `cat taggarr/services/__init__.py`

**Step 2: Update exports**

Update to export the new client classes instead of modules.

**Step 3: Commit**

```bash
git add taggarr/services/__init__.py
git commit -m "refactor: update services exports for client classes"
```

---

## Task 14: Manual Integration Test

**Step 1: Create a minimal test config**

Create `taggarr.yaml` with a single dry-run instance pointing to a test path.

**Step 2: Run with dry-run**

```bash
python main.py --dry-run
```

Expected: Logs show config loaded, instance processed, no actual API calls.

**Step 3: Test instance filtering**

```bash
python main.py --instances sonarr --dry-run
```

Expected: Only processes the specified instance.

**Step 4: Test missing config error**

```bash
rm taggarr.yaml
python main.py
```

Expected: Clear error message listing searched config locations.

---

## Summary

13 tasks total:

1. Add PyYAML dependency
2. Create config data classes
3. Create YAML config loader
4. Convert SonarrClient to class
5. Convert RadarrClient to class
6. Refactor TV processor
7. Refactor movies processor
8. Update package init
9. Update logging setup
10. Update CLI
11. Delete old config module
12. Create example config
13. Update services **init**.py
14. Manual integration test
