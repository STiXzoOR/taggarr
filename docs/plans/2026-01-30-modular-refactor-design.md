# Modular Refactor Design

**Date:** 2026-01-30
**Status:** Approved
**Goal:** Refactor single-file `main.py` (~1000 lines) into a modular package structure for maintainability

## Overview

Split taggarr into a layered package structure organized by responsibility:

- **Config** - Environment variables and constants
- **Services** - External integrations (Sonarr, Radarr, mediainfo)
- **Storage** - JSON persistence
- **Processors** - Business logic for TV and movie scanning
- **Utilities** - Language handling, NFO parsing, logging

## Package Structure

```
taggarr/
├── __init__.py          # Package version, run(), run_loop()
├── config.py            # Environment variables, constants
├── logging_setup.py     # Logger configuration
├── languages.py         # pycountry utilities, language code handling
├── nfo.py               # NFO file parsing and updates
├── services/
│   ├── __init__.py
│   ├── sonarr.py        # Sonarr API client
│   ├── radarr.py        # Radarr API client
│   └── media.py         # mediainfo audio analysis
├── storage/
│   ├── __init__.py
│   └── json_store.py    # taggarr.json read/write
└── processors/
    ├── __init__.py
    ├── tv.py            # TV show scanning, tag determination
    └── movies.py        # Movie scanning, tag determination

main.py                  # CLI entry point (~40 lines)
```

## Module Details

### config.py

All environment variables in one place:

```python
import os
from dotenv import load_dotenv

load_dotenv()

# Sonarr
SONARR_API_KEY = os.getenv("SONARR_API_KEY")
SONARR_URL = os.getenv("SONARR_URL")
ROOT_TV_PATH = os.getenv("ROOT_TV_PATH")

# Radarr
RADARR_API_KEY = os.getenv("RADARR_API_KEY")
RADARR_URL = os.getenv("RADARR_URL")
ROOT_MOVIE_PATH = os.getenv("ROOT_MOVIE_PATH")

# Tags
TAG_DUB = os.getenv("TAG_DUB", "dub")
TAG_SEMI = os.getenv("TAG_SEMI", "semi-dub")
TAG_WRONG_DUB = os.getenv("TAG_WRONG", "wrong-dub")

# Behavior
RUN_INTERVAL_SECONDS = int(os.getenv("RUN_INTERVAL_SECONDS", 7200))
START_RUNNING = os.getenv("START_RUNNING", "true").lower() == "true"
QUICK_MODE = os.getenv("QUICK_MODE", "false").lower() == "true"
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"
WRITE_MODE = int(os.getenv("WRITE_MODE", 0))
TARGET_LANGUAGES = [lang.strip().lower() for lang in os.getenv("TARGET_LANGUAGES", "en").split(",")]
TARGET_GENRE = os.getenv("TARGET_GENRE")
TARGET_GENRE_MOVIES = os.getenv("TARGET_GENRE_MOVIES")
ADD_TAG_TO_GENRE = os.getenv("ADD_TAG_TO_GENRE", "false").lower() == "true"

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_PATH = os.getenv("LOG_PATH", "/logs")

# Derived
SONARR_ENABLED = all([SONARR_API_KEY, SONARR_URL, ROOT_TV_PATH])
RADARR_ENABLED = all([RADARR_API_KEY, RADARR_URL, ROOT_MOVIE_PATH])

# JSON paths (computed)
TAGGARR_JSON_PATH = os.path.join(ROOT_TV_PATH, "taggarr.json") if ROOT_TV_PATH else None
TAGGARR_MOVIES_JSON_PATH = os.path.join(ROOT_MOVIE_PATH, "taggarr.json") if ROOT_MOVIE_PATH else None
```

### logging_setup.py

Logger factory, avoids stdlib naming conflict:

```python
import os
import logging
from datetime import datetime
from taggarr import __version__
from taggarr.config import LOG_LEVEL, LOG_PATH

def setup_logging():
    os.makedirs(LOG_PATH, exist_ok=True)
    log_file = os.path.join(LOG_PATH, f"taggarr({__version__})_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

    logger = logging.getLogger("taggarr")
    logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

    return logger
```

Other modules use `logging.getLogger("taggarr")` to access the logger.

### languages.py

Language code utilities using pycountry:

```python
import pycountry

def get_aliases(code_or_name):
    """Get all known aliases for a language (alpha_2, alpha_3, name, regional variants)."""
    if not code_or_name:
        return set()

    code_or_name = code_or_name.lower()
    aliases = set()

    try:
        lang = (
            pycountry.languages.get(alpha_2=code_or_name)
            or pycountry.languages.get(alpha_3=code_or_name)
            or pycountry.languages.lookup(code_or_name)
        )
    except Exception:
        return aliases

    if lang:
        if hasattr(lang, 'alpha_2'): aliases.add(lang.alpha_2.lower())
        if hasattr(lang, 'alpha_3'): aliases.add(lang.alpha_3.lower())
        aliases.add(lang.name.lower())

    # Add regional variants
    for suffix in ['-us', '-gb', '-ca', '-au', '-fr', '-de', '-jp', '-kr', '-cn', '-tw', '-ru']:
        aliases.update(a + suffix for a in list(aliases))

    return aliases

def get_primary_code(lang):
    """Get ISO 639-1 code (2-letter) for a language."""
    try:
        result = pycountry.languages.get(name=lang) or pycountry.languages.lookup(lang)
        return result.alpha_2.lower()
    except Exception:
        return lang.lower()[:2]

def build_language_codes(target_languages):
    """Build set of all acceptable language codes from target languages."""
    codes = set()
    for lang in target_languages:
        codes.update(get_aliases(lang))
    return codes
```

### nfo.py

NFO file parsing and updates:

```python
import os
import logging
import xml.etree.ElementTree as ET

logger = logging.getLogger("taggarr")

MANAGED_TAGS = {"dub", "semi-dub", "wrong-dub"}

def safe_parse(path):
    """Parse NFO file, handling common corruption issues."""
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    if "</tvshow>" in content:
        content = content.split("</tvshow>")[0] + "</tvshow>"
    return ET.fromstring(content)

def get_genres(nfo_path):
    """Extract genre list from NFO file."""
    try:
        root = safe_parse(nfo_path)
        return [g.text.lower() for g in root.findall("genre") if g.text]
    except Exception as e:
        logger.warning(f"Genre parsing failed for {nfo_path}: {e}")
        return []

def update_tag(nfo_path, tag_value, dry_run=False):
    """Update <tag> element in NFO file."""
    _update_tag_impl(nfo_path, tag_value, dry_run)

def update_movie_tag(nfo_path, tag_value, dry_run=False):
    """Update <tag> element in movie NFO file."""
    _update_tag_impl(nfo_path, tag_value, dry_run, is_movie=True)

def _update_tag_impl(nfo_path, tag_value, dry_run, is_movie=False):
    """Shared implementation for tag updates."""
    try:
        tree = ET.parse(nfo_path)
        root = tree.getroot()

        # Remove existing managed tags
        for t in root.findall("tag"):
            if t.text and t.text.strip().lower() in MANAGED_TAGS:
                root.remove(t)

        # Insert new tag at first position
        new_tag = ET.Element("tag")
        new_tag.text = tag_value

        insert_index = 0
        for i, elem in enumerate(root):
            if elem.tag == "tag":
                insert_index = i
                break
        root.insert(insert_index, new_tag)

        if dry_run:
            logger.info(f"[Dry Run] Would update <tag>{tag_value}</tag> in {os.path.basename(nfo_path)}")
        else:
            ET.indent(tree, space="  ")
            tree.write(nfo_path, encoding="utf-8", xml_declaration=False)
            logger.info(f"Updated <tag>{tag_value}</tag> in {os.path.basename(nfo_path)}")
    except Exception as e:
        logger.warning(f"Failed to update tag in {nfo_path}: {e}")

def update_genre(nfo_path, should_have_dub, dry_run=False):
    """Add or remove <genre>Dub</genre> based on tag status."""
    try:
        tree = ET.parse(nfo_path)
        root = tree.getroot()
        genres = [g.text.strip().lower() for g in root.findall("genre") if g.text]
        has_dub = "dub" in genres

        if should_have_dub == has_dub:
            return  # No change needed

        if should_have_dub and not has_dub:
            new_genre = ET.Element("genre")
            new_genre.text = "Dub"
            first_genre = root.find("genre")
            idx = list(root).index(first_genre) if first_genre is not None else len(root)
            root.insert(idx, new_genre)
            logger.info(f"Adding <genre>Dub</genre> to {os.path.basename(nfo_path)}")
        elif not should_have_dub and has_dub:
            for g in root.findall("genre"):
                if g.text and g.text.strip().lower() == "dub":
                    root.remove(g)
            logger.info(f"Removing <genre>Dub</genre> from {os.path.basename(nfo_path)}")

        if not dry_run:
            ET.indent(tree, space="  ")
            tree.write(nfo_path, encoding="utf-8", xml_declaration=False)
    except Exception as e:
        logger.warning(f"Failed to update genre in {nfo_path}: {e}")
```

### services/sonarr.py

Sonarr API client:

```python
import os
import time
import logging
import requests
from taggarr.config import SONARR_URL, SONARR_API_KEY

logger = logging.getLogger("taggarr")

def get_series_by_path(path):
    """Find series by folder path."""
    try:
        resp = requests.get(f"{SONARR_URL}/api/v3/series", headers={"X-Api-Key": SONARR_API_KEY})
        for s in resp.json():
            if os.path.basename(s['path']) == os.path.basename(path):
                return s
    except Exception as e:
        logger.warning(f"Sonarr lookup failed: {e}")
    return None

def get_series_id(path):
    """Get just the series ID."""
    series = get_series_by_path(path)
    return series['id'] if series else None

def add_tag(series_id, tag, dry_run=False):
    """Add a tag to a series."""
    if dry_run:
        logger.info(f"[Dry Run] Would add tag '{tag}' to series {series_id}")
        return
    tag_id = _get_or_create_tag(tag)
    _modify_series_tags(series_id, tag_id, remove=False)

def remove_tag(series_id, tag, dry_run=False):
    """Remove a tag from a series."""
    if dry_run:
        logger.info(f"[Dry Run] Would remove tag '{tag}' from series {series_id}")
        return
    tag_id = _get_tag_id(tag)
    if tag_id:
        _modify_series_tags(series_id, tag_id, remove=True)

def refresh_series(series_id, dry_run=False):
    """Trigger a series refresh in Sonarr."""
    if dry_run:
        logger.info(f"[Dry Run] Would trigger refresh for series {series_id}")
        return
    try:
        url = f"{SONARR_URL}/api/v3/command"
        payload = {"name": "RefreshSeries", "seriesId": series_id}
        requests.post(url, json=payload, headers={"X-Api-Key": SONARR_API_KEY}, timeout=10)
        logger.debug(f"Sonarr refresh triggered for series ID: {series_id}")
    except Exception as e:
        logger.warning(f"Failed to trigger Sonarr refresh: {e}")

def _get_tag_id(tag):
    """Get tag ID by label."""
    try:
        r = requests.get(f"{SONARR_URL}/api/v3/tag", headers={"X-Api-Key": SONARR_API_KEY})
        for t in r.json():
            if t["label"].lower() == tag.lower():
                return t["id"]
    except Exception:
        pass
    return None

def _get_or_create_tag(tag):
    """Get existing tag ID or create new one."""
    tag_id = _get_tag_id(tag)
    if tag_id is None:
        r = requests.post(f"{SONARR_URL}/api/v3/tag", headers={"X-Api-Key": SONARR_API_KEY}, json={"label": tag})
        tag_id = r.json()["id"]
        logger.debug(f"Created new Sonarr tag '{tag}' with ID {tag_id}")
    return tag_id

def _modify_series_tags(series_id, tag_id, remove=False):
    """Add or remove a tag from series."""
    try:
        s_url = f"{SONARR_URL}/api/v3/series/{series_id}"
        s_data = requests.get(s_url, headers={"X-Api-Key": SONARR_API_KEY}).json()

        if remove and tag_id in s_data["tags"]:
            s_data["tags"].remove(tag_id)
            logger.debug(f"Removing tag ID {tag_id} from series {series_id}")
        elif not remove and tag_id not in s_data["tags"]:
            s_data["tags"].append(tag_id)
            logger.debug(f"Adding tag ID {tag_id} to series {series_id}")

        requests.put(s_url, headers={"X-Api-Key": SONARR_API_KEY}, json=s_data)
        time.sleep(0.5)
    except Exception as e:
        logger.warning(f"Failed to modify series tags: {e}")
```

### services/radarr.py

Same pattern as sonarr.py with movie-specific endpoints.

### services/media.py

Audio analysis using mediainfo:

```python
import logging
from pymediainfo import MediaInfo

logger = logging.getLogger("taggarr")

def analyze_audio(video_path):
    """Extract audio language codes from a video file."""
    try:
        media_info = MediaInfo.parse(video_path)
        langs = set()

        for track in media_info.tracks:
            if track.track_type == "Audio":
                lang = (track.language or "").strip().lower()
                title = (track.title or "").strip().lower()

                if lang:
                    langs.add(lang)
                elif "track 1" in title or "audio 1" in title or title == "":
                    langs.add("__fallback_original__")

        logger.debug(f"Analyzed {video_path}, found languages: {sorted(langs)}")
        return list(langs)
    except Exception as e:
        logger.warning(f"Audio analysis failed for {video_path}: {e}")
        return []
```

### storage/json_store.py

Unified JSON handling:

```python
import os
import re
import json
import logging
from taggarr import __version__

logger = logging.getLogger("taggarr")

def load(json_path, key="series"):
    """Load taggarr.json, returning empty dict if missing/corrupted."""
    if not json_path or not os.path.exists(json_path):
        logger.info(f"No taggarr.json found — starting fresh.")
        return {key: {}}

    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
            logger.debug(f"Loaded taggarr.json with {len(data.get(key, {}))} entries.")
            return data
    except Exception as e:
        logger.warning(f"taggarr.json corrupted: {e}")
        backup_path = json_path + ".bak"
        os.rename(json_path, backup_path)
        logger.warning(f"Corrupted file moved to: {backup_path}")
        return {key: {}}

def save(json_path, data, key="series"):
    """Save taggarr.json with compacted formatting."""
    if not json_path:
        return

    data["version"] = __version__
    ordered = {"version": __version__}
    ordered.update({k: v for k, v in data.items() if k != "version"})

    raw_json = json.dumps(ordered, indent=2, ensure_ascii=False)
    compact_json = _compact_lists(raw_json)

    with open(json_path, 'w') as f:
        f.write(compact_json)
    logger.debug("taggarr.json saved successfully.")

def _compact_lists(raw_json):
    """Compact episode and language lists onto single lines."""
    # Compact E## lists
    result = re.sub(
        r'(\[\s*\n\s*)((?:\s*"E\d{2}",?\s*\n?)+)(\s*\])',
        lambda m: '[{}]'.format(', '.join(re.findall(r'"E\d{2}"', m.group(2)))),
        raw_json
    )
    # Compact language lists
    result = re.sub(
        r'("(?:original_dub|dub|missing_dub|unexpected_languages|languages)": )\[\s*\n\s*((?:\s*"[^"]+",?\s*\n?)+)(\s*\])',
        lambda m: '{}[{}]'.format(m.group(1), ', '.join(f'"{x}"' for x in re.findall(r'"([^"]+)"', m.group(2)))),
        result
    )
    return result
```

### processors/tv.py

TV show processing orchestration:

```python
import os
import re
import logging
from datetime import datetime

from taggarr.config import (
    ROOT_TV_PATH, TARGET_GENRE, TARGET_LANGUAGES, TAG_DUB, TAG_SEMI,
    TAG_WRONG_DUB, ADD_TAG_TO_GENRE, QUICK_MODE, DRY_RUN, WRITE_MODE
)
from taggarr.services import sonarr, media
from taggarr import nfo, languages

logger = logging.getLogger("taggarr")

# Build language codes at module load
LANGUAGE_CODES = languages.build_language_codes(TARGET_LANGUAGES)

def process_all(opts, taggarr_data):
    """Process all TV shows in the library."""
    quick = opts.quick or QUICK_MODE
    dry_run = opts.dry_run or DRY_RUN
    write_mode = opts.write_mode or WRITE_MODE

    for show_folder in sorted(os.listdir(ROOT_TV_PATH)):
        show_path = os.path.abspath(os.path.join(ROOT_TV_PATH, show_folder))
        if not os.path.isdir(show_path):
            continue

        # Check if scan needed
        if write_mode == 0 and not _needs_scan(show_path, taggarr_data):
            logger.info(f"Skipping {show_folder} - no changes")
            continue

        # Genre filter
        nfo_path = os.path.join(show_path, "tvshow.nfo")
        if not _passes_genre_filter(nfo_path):
            continue

        # Get Sonarr metadata
        series = sonarr.get_series_by_path(show_path)
        if not series:
            logger.warning(f"No Sonarr metadata for {show_folder}")
            continue

        logger.info(f"Processing show: {show_folder}")
        series_id = series['id']

        # Handle remove mode
        if write_mode == 2:
            _remove_all_tags(series_id, show_path, taggarr_data, dry_run)
            continue

        # Scan and determine tag
        tag, seasons = scan_show(show_path, series, quick)
        logger.info(f"Tagged as {tag or 'no tag (original)'}")

        # Apply tags to Sonarr
        _apply_tags(series_id, tag, dry_run)

        # Update NFO
        if ADD_TAG_TO_GENRE:
            nfo.update_genre(nfo_path, tag == TAG_DUB, dry_run)
        if tag in [TAG_DUB, TAG_SEMI, TAG_WRONG_DUB]:
            nfo.update_tag(nfo_path, tag, dry_run)

        # Save state
        taggarr_data["series"][show_path] = _build_show_entry(show_folder, tag, seasons, series)

        if write_mode == 1:
            sonarr.refresh_series(series_id, dry_run)

    return taggarr_data

def scan_show(show_path, series_meta, quick=False):
    """Scan all seasons and determine overall tag."""
    seasons = {}
    has_wrong, has_dub = False, False

    for entry in sorted(os.listdir(show_path)):
        season_path = os.path.join(show_path, entry)
        if not (os.path.isdir(season_path) and entry.lower().startswith("season")):
            continue

        logger.info(f"Scanning season: {entry}")
        stats = scan_season(season_path, series_meta, quick)
        stats["last_modified"] = os.path.getmtime(season_path)
        stats["status"] = _determine_season_status(stats)

        has_wrong = has_wrong or bool(stats["unexpected_languages"])
        has_dub = has_dub or bool(stats["dub"])
        seasons[entry] = stats

    # Determine final tag
    statuses = [s["status"] for s in seasons.values()]
    if has_wrong:
        return TAG_WRONG_DUB, seasons
    elif all(s == "fully-dub" for s in statuses):
        return TAG_DUB, seasons
    elif any(s in ("fully-dub", "semi-dub") for s in statuses):
        return TAG_SEMI, seasons

    return None, seasons

def scan_season(season_path, series_meta, quick=False):
    """Scan episodes in a season folder."""
    video_exts = ['.mkv', '.mp4', '.m4v', '.avi', '.webm', '.mov', '.mxf']
    files = sorted([f for f in os.listdir(season_path) if os.path.splitext(f)[1].lower() in video_exts])
    if quick and files:
        files = [files[0]]

    # Get original language codes
    original_lang = series_meta.get("originalLanguage", "")
    if isinstance(original_lang, dict):
        original_lang_name = original_lang.get("name", "").lower()
    else:
        original_lang_name = str(original_lang).lower()

    original_codes = languages.get_aliases(original_lang_name)
    accepted_languages = LANGUAGE_CODES.union(original_codes)

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
            logger.info(f"Audio not labelled for {ep_name} - assuming original")
            continue

        langs_set = set(langs)
        has_target = langs_set.intersection(LANGUAGE_CODES)

        # Check for missing target languages
        langs_aliases = set()
        for l in langs:
            langs_aliases.update(languages.get_aliases(l))

        missing_target = set()
        for t in TARGET_LANGUAGES:
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
        for l in langs:
            if l not in LANGUAGE_CODES and l not in original_codes:
                stats["unexpected_languages"].append(l)

    stats["unexpected_languages"] = sorted(set(stats["unexpected_languages"]))
    return stats

def _needs_scan(show_path, taggarr_data):
    """Check if show needs scanning based on modification times."""
    saved = taggarr_data["series"].get(show_path, {})
    saved_seasons = saved.get("seasons", {})

    # New show
    if show_path not in taggarr_data["series"]:
        return True

    # Check for new or modified seasons
    for d in os.listdir(show_path):
        season_path = os.path.join(show_path, d)
        if os.path.isdir(season_path) and d.lower().startswith("season"):
            current_mtime = os.path.getmtime(season_path)
            saved_mtime = saved_seasons.get(d, {}).get("last_modified", 0)
            if current_mtime > saved_mtime:
                return True
            if d not in saved_seasons:
                return True

    return False

def _passes_genre_filter(nfo_path):
    """Check if show passes genre filter."""
    if not TARGET_GENRE:
        return True
    if not os.path.exists(nfo_path):
        logger.debug(f"No NFO found: {nfo_path}")
        return False
    genres = nfo.get_genres(nfo_path)
    if TARGET_GENRE.lower() not in genres:
        logger.info(f"Skipping - genre mismatch")
        return False
    return True

def _apply_tags(series_id, tag, dry_run):
    """Apply appropriate tags and remove conflicting ones."""
    if tag:
        sonarr.add_tag(series_id, tag, dry_run)
        if tag == TAG_WRONG_DUB:
            sonarr.remove_tag(series_id, TAG_SEMI, dry_run)
            sonarr.remove_tag(series_id, TAG_DUB, dry_run)
        elif tag == TAG_SEMI:
            sonarr.remove_tag(series_id, TAG_WRONG_DUB, dry_run)
            sonarr.remove_tag(series_id, TAG_DUB, dry_run)
        elif tag == TAG_DUB:
            sonarr.remove_tag(series_id, TAG_WRONG_DUB, dry_run)
            sonarr.remove_tag(series_id, TAG_SEMI, dry_run)
    else:
        for t in [TAG_DUB, TAG_SEMI, TAG_WRONG_DUB]:
            sonarr.remove_tag(series_id, t, dry_run)

def _remove_all_tags(series_id, show_path, taggarr_data, dry_run):
    """Remove all tags (write_mode=2)."""
    for tag in [TAG_DUB, TAG_SEMI, TAG_WRONG_DUB]:
        sonarr.remove_tag(series_id, tag, dry_run)
    if show_path in taggarr_data["series"]:
        del taggarr_data["series"][show_path]

def _determine_season_status(stats):
    """Determine season status from stats."""
    if stats["unexpected_languages"]:
        return "wrong-dub"
    elif not stats["missing_dub"] and stats["dub"]:
        return "fully-dub"
    elif stats["dub"]:
        return "semi-dub"
    return "original"

def _build_show_entry(show_folder, tag, seasons, series):
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
    }
```

### processors/movies.py

Movie processing - same pattern, simpler structure (no seasons).

### taggarr/**init**.py

Package entry point:

```python
__description__ = "Dub Analysis & Tagging."
__author__ = "BASSHOUS3"
__version__ = "0.5.0"

import time
import logging

from taggarr.config import (
    SONARR_ENABLED, RADARR_ENABLED,
    TAGGARR_JSON_PATH, TAGGARR_MOVIES_JSON_PATH,
    RUN_INTERVAL_SECONDS
)
from taggarr.logging_setup import setup_logging
from taggarr.storage import json_store
from taggarr.processors import tv, movies

logger = None

def run(opts):
    """Run a single scan cycle."""
    global logger
    if logger is None:
        logger = setup_logging()

    logger.info(f"Taggarr - {__description__}")
    logger.info(f"Taggarr - v{__version__} started.")
    logger.info("Starting Taggarr scan...")

    # Process TV shows
    if SONARR_ENABLED:
        logger.info("Sonarr enabled - processing TV shows...")
        taggarr_data = json_store.load(TAGGARR_JSON_PATH, key="series")
        taggarr_data = tv.process_all(opts, taggarr_data)
        json_store.save(TAGGARR_JSON_PATH, taggarr_data, key="series")
    else:
        logger.info("Sonarr not configured - skipping TV shows")

    # Process movies
    if RADARR_ENABLED:
        logger.info("Radarr enabled - processing movies...")
        taggarr_movies = json_store.load(TAGGARR_MOVIES_JSON_PATH, key="movies")
        taggarr_movies = movies.process_all(opts, taggarr_movies)
        json_store.save(TAGGARR_MOVIES_JSON_PATH, taggarr_movies, key="movies")
    else:
        logger.info("Radarr not configured - skipping movies")

    logger.info("Finished Taggarr scan.")
    logger.info(f"Next scan in {RUN_INTERVAL_SECONDS / 3600} hours.")

def run_loop(opts):
    """Run scans continuously at configured interval."""
    while True:
        run(opts)
        time.sleep(RUN_INTERVAL_SECONDS)
```

### main.py

Thin CLI wrapper:

```python
#!/usr/bin/env python3
"""Taggarr - Dub Analysis & Tagging CLI"""

import argparse
import time
import taggarr
from taggarr.config import START_RUNNING, WRITE_MODE, RUN_INTERVAL_SECONDS

def main():
    parser = argparse.ArgumentParser(description=taggarr.__description__)
    parser.add_argument('--write-mode', type=int, choices=[0, 1, 2],
                        default=WRITE_MODE,
                        help="0=default, 1=rewrite all, 2=remove all")
    parser.add_argument('--quick', action='store_true',
                        help="Scan only first episode per season")
    parser.add_argument('--dry-run', action='store_true',
                        help="No API calls or file edits")
    opts = parser.parse_args()

    if START_RUNNING:
        taggarr.run_loop(opts)
    elif any(vars(opts).values()):
        taggarr.run(opts)
    else:
        while True:
            time.sleep(RUN_INTERVAL_SECONDS)

if __name__ == '__main__':
    main()
```

## Import Structure

```
main.py
  └── taggarr (package)
        ├── config (no deps)
        ├── logging_setup (← config, __version__)
        ├── languages (← pycountry)
        ├── nfo (standalone)
        ├── storage/json_store (← config, __version__)
        ├── services/sonarr (← config)
        ├── services/radarr (← config)
        ├── services/media (← pymediainfo)
        └── processors/tv, movies (← all above)
```

## Migration Strategy

1. Create package structure with empty `__init__.py` files
2. Extract `config.py` first (no internal dependencies)
3. Extract utilities: `languages.py`, `logging_setup.py`
4. Extract `storage/json_store.py`
5. Extract services: `sonarr.py`, `radarr.py`, `media.py`
6. Extract `nfo.py`
7. Extract processors: `tv.py`, `movies.py`
8. Create package `__init__.py` with `run()` and `run_loop()`
9. Replace `main.py` with thin CLI wrapper
10. Test with `--dry-run` to verify behavior unchanged

## Backward Compatibility

- CLI interface unchanged (`python main.py --quick --dry-run`)
- Environment variables unchanged
- `taggarr.json` format unchanged
- Docker usage unchanged

## Testing Benefits

Each module can be unit tested in isolation:

- Mock `requests` for Sonarr/Radarr tests
- Mock `MediaInfo.parse` for media tests
- Use temp files for JSON storage tests
