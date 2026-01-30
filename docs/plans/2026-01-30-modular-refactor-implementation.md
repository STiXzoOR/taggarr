# Modular Refactor Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Refactor single-file `main.py` (~1000 lines) into a modular package structure

**Architecture:** Layer-based separation - config, services (Sonarr/Radarr/media), storage (JSON), processors (TV/movies), utilities (languages, NFO, logging). Each module is independently testable.

**Tech Stack:** Python 3, pycountry, pymediainfo, requests, python-dotenv

**Design Doc:** `docs/plans/2026-01-30-modular-refactor-design.md`

---

## Task 1: Create Package Directory Structure

**Files:**

- Create: `taggarr/__init__.py`
- Create: `taggarr/services/__init__.py`
- Create: `taggarr/storage/__init__.py`
- Create: `taggarr/processors/__init__.py`

**Step 1: Create directories and empty init files**

```bash
mkdir -p taggarr/services taggarr/storage taggarr/processors
touch taggarr/__init__.py taggarr/services/__init__.py taggarr/storage/__init__.py taggarr/processors/__init__.py
```

**Step 2: Add minimal package init**

In `taggarr/__init__.py`:

```python
__description__ = "Dub Analysis & Tagging."
__author__ = "BASSHOUS3"
__version__ = "0.5.0"
```

**Step 3: Verify structure**

```bash
find taggarr -type f -name "*.py"
```

Expected:

```
taggarr/__init__.py
taggarr/services/__init__.py
taggarr/storage/__init__.py
taggarr/processors/__init__.py
```

**Step 4: Commit**

```bash
git add taggarr/
git commit -m "chore: create taggarr package structure"
```

---

## Task 2: Extract Configuration Module

**Files:**

- Create: `taggarr/config.py`
- Reference: `main.py:19-50` (env var definitions)

**Step 1: Create config.py with all environment variables**

```python
"""Configuration loaded from environment variables."""

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

# JSON paths
TAGGARR_JSON_PATH = os.path.join(ROOT_TV_PATH, "taggarr.json") if ROOT_TV_PATH else None
TAGGARR_MOVIES_JSON_PATH = os.path.join(ROOT_MOVIE_PATH, "taggarr.json") if ROOT_MOVIE_PATH else None
```

**Step 2: Verify imports work**

```bash
python -c "from taggarr.config import SONARR_ENABLED, TAG_DUB; print('config ok')"
```

Expected: `config ok`

**Step 3: Commit**

```bash
git add taggarr/config.py
git commit -m "feat: extract config module from main.py"
```

---

## Task 3: Extract Languages Module

**Files:**

- Create: `taggarr/languages.py`
- Reference: `main.py:418-461` (language utilities)

**Step 1: Create languages.py**

```python
"""Language code utilities using pycountry."""

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
        if hasattr(lang, 'alpha_2'):
            aliases.add(lang.alpha_2.lower())
        if hasattr(lang, 'alpha_3'):
            aliases.add(lang.alpha_3.lower())
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

**Step 2: Verify imports work**

```bash
python -c "from taggarr.languages import get_aliases; print(get_aliases('en'))"
```

Expected: Set containing `en`, `eng`, `english`, and regional variants

**Step 3: Commit**

```bash
git add taggarr/languages.py
git commit -m "feat: extract languages module from main.py"
```

---

## Task 4: Extract Logging Setup Module

**Files:**

- Create: `taggarr/logging_setup.py`
- Reference: `main.py:52-79` (logging setup)

**Step 1: Create logging_setup.py**

```python
"""Logging configuration for taggarr."""

import os
import logging
from datetime import datetime

from taggarr import __version__
from taggarr.config import LOG_LEVEL, LOG_PATH


def setup_logging():
    """Configure and return the taggarr logger."""
    os.makedirs(LOG_PATH, exist_ok=True)
    log_file = os.path.join(
        LOG_PATH,
        f"taggarr({__version__})_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    )

    logger = logging.getLogger("taggarr")
    logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

    logger.debug(f"Log file created: {log_file}")

    return logger
```

**Step 2: Verify imports work**

```bash
LOG_PATH=/tmp python -c "from taggarr.logging_setup import setup_logging; logger = setup_logging(); logger.info('test')"
```

Expected: Log output with timestamp

**Step 3: Commit**

```bash
git add taggarr/logging_setup.py
git commit -m "feat: extract logging_setup module from main.py"
```

---

## Task 5: Extract Media Service

**Files:**

- Create: `taggarr/services/media.py`
- Reference: `main.py:186-209` (analyze_audio function)

**Step 1: Create media.py**

```python
"""Media file analysis using pymediainfo."""

import logging
from pymediainfo import MediaInfo

logger = logging.getLogger("taggarr")


def analyze_audio(video_path):
    """Extract audio language codes from a video file.

    Returns list of language codes found in audio tracks.
    Uses "__fallback_original__" when track has no language but appears to be main audio.
    """
    try:
        media_info = MediaInfo.parse(video_path)
        langs = set()
        fallback_detected = False

        for track in media_info.tracks:
            if track.track_type == "Audio":
                lang = (track.language or "").strip().lower()
                title = (track.title or "").strip().lower()

                if lang:
                    langs.add(lang)
                elif "track 1" in title or "audio 1" in title or title == "":
                    langs.add("__fallback_original__")
                    fallback_detected = True

        logger.debug(f"Analyzed {video_path}, found audio languages: {sorted(langs)}")
        if fallback_detected:
            logger.debug(f"Fallback language detection used in {video_path}")
        return list(langs)
    except Exception as e:
        logger.warning(f"Audio analysis failed for {video_path}: {e}")
        return []
```

**Step 2: Commit**

```bash
git add taggarr/services/media.py
git commit -m "feat: extract media service from main.py"
```

---

## Task 6: Extract Sonarr Service

**Files:**

- Create: `taggarr/services/sonarr.py`
- Reference: `main.py:463-523` (Sonarr API functions)

**Step 1: Create sonarr.py**

```python
"""Sonarr API client."""

import os
import time
import logging
import requests

from taggarr.config import SONARR_URL, SONARR_API_KEY

logger = logging.getLogger("taggarr")


def get_series_by_path(path):
    """Find series by folder path."""
    try:
        resp = requests.get(
            f"{SONARR_URL}/api/v3/series",
            headers={"X-Api-Key": SONARR_API_KEY}
        )
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
        r = requests.get(
            f"{SONARR_URL}/api/v3/tag",
            headers={"X-Api-Key": SONARR_API_KEY}
        )
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
        r = requests.post(
            f"{SONARR_URL}/api/v3/tag",
            headers={"X-Api-Key": SONARR_API_KEY},
            json={"label": tag}
        )
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

**Step 2: Commit**

```bash
git add taggarr/services/sonarr.py
git commit -m "feat: extract sonarr service from main.py"
```

---

## Task 7: Extract Radarr Service

**Files:**

- Create: `taggarr/services/radarr.py`
- Reference: `main.py:525-576` (Radarr API functions)

**Step 1: Create radarr.py**

```python
"""Radarr API client."""

import os
import time
import logging
import requests

from taggarr.config import RADARR_URL, RADARR_API_KEY

logger = logging.getLogger("taggarr")


def get_movies():
    """Fetch all movies from Radarr API."""
    try:
        resp = requests.get(
            f"{RADARR_URL}/api/v3/movie",
            headers={"X-Api-Key": RADARR_API_KEY}
        )
        return resp.json()
    except Exception as e:
        logger.warning(f"Failed to fetch Radarr movies: {e}")
        return []


def get_movie_by_path(path):
    """Find a specific movie by its folder path."""
    try:
        resp = requests.get(
            f"{RADARR_URL}/api/v3/movie",
            headers={"X-Api-Key": RADARR_API_KEY}
        )
        for m in resp.json():
            if os.path.basename(m['path']) == os.path.basename(path):
                return m
    except Exception as e:
        logger.warning(f"Radarr lookup failed: {e}")
    return None


def add_tag(movie_id, tag, dry_run=False):
    """Add a tag to a movie."""
    if dry_run:
        logger.info(f"[Dry Run] Would add tag '{tag}' to movie {movie_id}")
        return
    tag_id = _get_or_create_tag(tag)
    _modify_movie_tags(movie_id, tag_id, remove=False)


def remove_tag(movie_id, tag, dry_run=False):
    """Remove a tag from a movie."""
    if dry_run:
        logger.info(f"[Dry Run] Would remove tag '{tag}' from movie {movie_id}")
        return
    tag_id = _get_tag_id(tag)
    if tag_id:
        _modify_movie_tags(movie_id, tag_id, remove=True)


def _get_tag_id(tag):
    """Get tag ID by label."""
    try:
        r = requests.get(
            f"{RADARR_URL}/api/v3/tag",
            headers={"X-Api-Key": RADARR_API_KEY}
        )
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
        r = requests.post(
            f"{RADARR_URL}/api/v3/tag",
            headers={"X-Api-Key": RADARR_API_KEY},
            json={"label": tag}
        )
        tag_id = r.json()["id"]
        logger.debug(f"Created new Radarr tag '{tag}' with ID {tag_id}")
    return tag_id


def _modify_movie_tags(movie_id, tag_id, remove=False):
    """Add or remove a tag from movie."""
    try:
        m_url = f"{RADARR_URL}/api/v3/movie/{movie_id}"
        m_data = requests.get(m_url, headers={"X-Api-Key": RADARR_API_KEY}).json()

        if remove and tag_id in m_data["tags"]:
            m_data["tags"].remove(tag_id)
            logger.debug(f"Removing tag ID {tag_id} from movie {movie_id}")
        elif not remove and tag_id not in m_data["tags"]:
            m_data["tags"].append(tag_id)
            logger.debug(f"Adding tag ID {tag_id} to movie {movie_id}")

        requests.put(m_url, headers={"X-Api-Key": RADARR_API_KEY}, json=m_data)
        time.sleep(0.5)
    except Exception as e:
        logger.warning(f"Failed to modify movie tags: {e}")
```

**Step 2: Commit**

```bash
git add taggarr/services/radarr.py
git commit -m "feat: extract radarr service from main.py"
```

---

## Task 8: Extract JSON Storage Module

**Files:**

- Create: `taggarr/storage/json_store.py`
- Reference: `main.py:82-184` (JSON load/save functions)

**Step 1: Create json_store.py**

```python
"""JSON storage for taggarr scan results."""

import os
import re
import json
import logging

from taggarr import __version__

logger = logging.getLogger("taggarr")


def load(json_path, key="series"):
    """Load taggarr.json, returning empty dict if missing/corrupted."""
    if not json_path:
        return {key: {}}

    if not os.path.exists(json_path):
        logger.info(f"No taggarr.json found at {json_path} — starting fresh.")
        return {key: {}}

    try:
        logger.info(f"taggarr.json found at {json_path}")
        with open(json_path, 'r') as f:
            data = json.load(f)
            logger.debug(f"Loaded taggarr.json with {len(data.get(key, {}))} entries.")
            return data
    except Exception as e:
        logger.warning(f"taggarr.json is corrupted: {e}")
        backup_path = json_path + ".bak"
        os.rename(json_path, backup_path)
        logger.warning(f"Corrupted file moved to: {backup_path}")
        return {key: {}}


def save(json_path, data, key="series"):
    """Save taggarr.json with compacted formatting."""
    if not json_path:
        return

    try:
        data["version"] = __version__
        ordered = {"version": __version__}
        ordered.update({k: v for k, v in data.items() if k != "version"})

        raw_json = json.dumps(ordered, indent=2, ensure_ascii=False)
        compact_json = _compact_lists(raw_json)

        with open(json_path, 'w') as f:
            f.write(compact_json)
        logger.debug("taggarr.json saved successfully.")
    except Exception as e:
        logger.warning(f"Failed to save taggarr.json: {e}")


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
        lambda m: '{}[{}]'.format(
            m.group(1),
            ', '.join(f'"{x}"' for x in re.findall(r'"([^"]+)"', m.group(2)))
        ),
        result
    )
    return result
```

**Step 2: Commit**

```bash
git add taggarr/storage/json_store.py
git commit -m "feat: extract json_store module from main.py"
```

---

## Task 9: Extract NFO Module

**Files:**

- Create: `taggarr/nfo.py`
- Reference: `main.py:578-666` (NFO functions)

**Step 1: Create nfo.py**

```python
"""NFO file parsing and updates for Kodi/Emby."""

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
    """Update <tag> element in TV show NFO file."""
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
            label = "movie NFO" if is_movie else "NFO"
            logger.info(f"Updated <tag>{tag_value}</tag> in {label}: {os.path.basename(nfo_path)}")
    except Exception as e:
        logger.warning(f"Failed to update <tag> in NFO: {e}")


def update_genre(nfo_path, should_have_dub, dry_run=False):
    """Add or remove <genre>Dub</genre> based on tag status."""
    try:
        tree = ET.parse(nfo_path)
        root = tree.getroot()
        genres = [g.text.strip().lower() for g in root.findall("genre") if g.text]
        has_dub = "dub" in genres

        if should_have_dub == has_dub:
            return  # No change needed

        modified = False

        if should_have_dub and not has_dub:
            new_genre = ET.Element("genre")
            new_genre.text = "Dub"
            first_genre = root.find("genre")
            if first_genre is not None:
                idx = list(root).index(first_genre)
            else:
                idx = len(root)
            root.insert(idx, new_genre)
            modified = True
            logger.info(f"Adding <genre>Dub</genre> to {os.path.basename(nfo_path)}")

        elif not should_have_dub and has_dub:
            for g in root.findall("genre"):
                if g.text and g.text.strip().lower() == "dub":
                    root.remove(g)
                    modified = True
            logger.info(f"Removing <genre>Dub</genre> from {os.path.basename(nfo_path)}")

        if modified and not dry_run:
            ET.indent(tree, space="  ")
            tree.write(nfo_path, encoding="utf-8", xml_declaration=False)
        elif modified and dry_run:
            logger.info(f"[Dry Run] Would update NFO file: {os.path.basename(nfo_path)}")

    except Exception as e:
        logger.warning(f"Failed to update NFO genre: {e}")
```

**Step 2: Commit**

```bash
git add taggarr/nfo.py
git commit -m "feat: extract nfo module from main.py"
```

---

## Task 10: Extract TV Processor

**Files:**

- Create: `taggarr/processors/tv.py`
- Reference: `main.py:304-414, 823-981` (TV show processing)

**Step 1: Create tv.py**

```python
"""TV show scanning and tagging processor."""

import os
import re
import logging
from datetime import datetime

from taggarr.config import (
    ROOT_TV_PATH, TARGET_GENRE, TARGET_LANGUAGES,
    TAG_DUB, TAG_SEMI, TAG_WRONG_DUB,
    ADD_TAG_TO_GENRE, QUICK_MODE, DRY_RUN, WRITE_MODE
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

        if not _passes_genre_filter(nfo_path):
            logger.info(f"Skipping {show_folder}: genre mismatch")
            continue

        logger.info(f"Processing show: {show_folder}")

        # Get Sonarr metadata
        series = sonarr.get_series_by_path(show_path)
        if not series:
            logger.warning(f"No Sonarr metadata for {show_folder}")
            continue

        series_id = series['id']

        # Handle remove mode
        if write_mode == 2:
            logger.info(f"Removing tags for {show_folder}")
            for tag in [TAG_DUB, TAG_SEMI, TAG_WRONG_DUB]:
                sonarr.remove_tag(series_id, tag, dry_run)
            if show_path in taggarr_data["series"]:
                del taggarr_data["series"][show_path]
            continue

        # Scan and determine tag
        tag, seasons = scan_show(show_path, series, quick)
        logger.info(f"Tagged as {tag or 'no tag (original)'}")

        # Apply tags to Sonarr
        _apply_tags(series_id, tag, dry_run)

        # Update NFO genre if configured
        if ADD_TAG_TO_GENRE:
            nfo.update_genre(nfo_path, tag == TAG_DUB, dry_run)

        # Update NFO tag
        if tag in [TAG_DUB, TAG_SEMI, TAG_WRONG_DUB]:
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
        stats = _scan_season(season_path, series_meta, quick)
        stats["last_modified"] = os.path.getmtime(season_path)
        stats["status"] = _determine_status(stats)

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


def _scan_season(season_path, series_meta, quick=False):
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
        has_target = langs_set.intersection(LANGUAGE_CODES)

        # Build aliases for detected languages
        langs_aliases = set()
        for lang in langs:
            langs_aliases.update(languages.get_aliases(lang))

        # Check for missing target languages
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
        for lang in langs:
            if lang not in LANGUAGE_CODES and lang not in original_codes:
                stats["unexpected_languages"].append(lang)

    stats["unexpected_languages"] = sorted(set(stats["unexpected_languages"]))
    return stats


def _has_changes(show_path, saved_seasons):
    """Check if any season has been modified."""
    for d in os.listdir(show_path):
        season_path = os.path.join(show_path, d)
        if os.path.isdir(season_path) and d.lower().startswith("season"):
            current_mtime = os.path.getmtime(season_path)
            saved_mtime = saved_seasons.get(d, {}).get("last_modified", 0)
            if current_mtime > saved_mtime:
                return True
    return False


def _has_new_seasons(show_path, saved_seasons):
    """Check if there are new season folders."""
    existing = set(saved_seasons.keys())
    current = set(
        d for d in os.listdir(show_path)
        if os.path.isdir(os.path.join(show_path, d)) and d.lower().startswith("season")
    )
    return len(current - existing) > 0


def _passes_genre_filter(nfo_path):
    """Check if show passes genre filter."""
    if not TARGET_GENRE:
        return True
    genres = nfo.get_genres(nfo_path)
    return TARGET_GENRE.lower() in genres


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
        logger.info("Removing all tags since it's original (no tag)")
        for t in [TAG_DUB, TAG_SEMI, TAG_WRONG_DUB]:
            sonarr.remove_tag(series_id, t, dry_run)


def _determine_status(stats):
    """Determine season status from stats."""
    if stats["unexpected_languages"]:
        return "wrong-dub"
    elif not stats["missing_dub"] and stats["dub"]:
        return "fully-dub"
    elif stats["dub"]:
        return "semi-dub"
    return "original"


def _build_entry(show_folder, tag, seasons, series, mtime):
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

**Step 2: Commit**

```bash
git add taggarr/processors/tv.py
git commit -m "feat: extract TV processor from main.py"
```

---

## Task 11: Extract Movies Processor

**Files:**

- Create: `taggarr/processors/movies.py`
- Reference: `main.py:212-302, 668-783` (movie processing)

**Step 1: Create movies.py**

```python
"""Movie scanning and tagging processor."""

import os
import logging
from datetime import datetime

from taggarr.config import (
    ROOT_MOVIE_PATH, TARGET_GENRE_MOVIES, TARGET_LANGUAGES,
    TAG_DUB, TAG_WRONG_DUB,
    QUICK_MODE, DRY_RUN, WRITE_MODE
)
from taggarr.services import radarr, media
from taggarr import nfo, languages

logger = logging.getLogger("taggarr")

# Build language codes at module load
LANGUAGE_CODES = languages.build_language_codes(TARGET_LANGUAGES)


def process_all(opts, taggarr_movies):
    """Process all movies in the library."""
    quick = opts.quick or QUICK_MODE
    dry_run = opts.dry_run or DRY_RUN
    write_mode = opts.write_mode or WRITE_MODE

    logger.info("Starting movie scan...")

    for movie_folder in sorted(os.listdir(ROOT_MOVIE_PATH)):
        movie_path = os.path.abspath(os.path.join(ROOT_MOVIE_PATH, movie_folder))
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
        movie_meta = radarr.get_movie_by_path(movie_path)
        if not movie_meta:
            logger.warning(f"No Radarr metadata for {movie_folder}")
            continue

        # Skip movies not yet downloaded
        if not movie_meta.get("hasFile", False):
            logger.debug(f"Skipping {movie_folder} - not yet downloaded")
            continue

        # Genre filter
        if TARGET_GENRE_MOVIES:
            genres = [g.lower() for g in movie_meta.get("genres", [])]
            if TARGET_GENRE_MOVIES.lower() not in genres:
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
            for tag in [TAG_DUB, TAG_WRONG_DUB]:
                radarr.remove_tag(movie_id, tag, dry_run)
            if movie_path in taggarr_movies["movies"]:
                del taggarr_movies["movies"][movie_path]
            continue

        # Scan movie
        scan_result = _scan_movie(movie_path, movie_meta)
        if scan_result is None:
            continue

        # Determine tag
        tag = _determine_tag(scan_result)
        logger.info(f"Tagged as {tag or 'no tag (original)'}")

        # Apply tags to Radarr
        if tag:
            radarr.add_tag(movie_id, tag, dry_run)
            if tag == TAG_WRONG_DUB:
                radarr.remove_tag(movie_id, TAG_DUB, dry_run)
            elif tag == TAG_DUB:
                radarr.remove_tag(movie_id, TAG_WRONG_DUB, dry_run)
        else:
            for t in [TAG_DUB, TAG_WRONG_DUB]:
                radarr.remove_tag(movie_id, t, dry_run)

        # Update NFO if applicable
        nfo_path = _find_nfo(movie_path, movie_folder)
        if nfo_path and tag in [TAG_DUB, TAG_WRONG_DUB]:
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


def _scan_movie(movie_path, movie_meta):
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


def _determine_tag(scan_result):
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
    for target in TARGET_LANGUAGES:
        target_aliases = languages.get_aliases(target)
        if not langs_aliases.intersection(target_aliases):
            has_all_targets = False
            break

    # Check for unexpected languages
    unexpected = []
    for lang in langs:
        if lang not in LANGUAGE_CODES and lang not in original_codes:
            unexpected.append(lang)

    if unexpected:
        return TAG_WRONG_DUB
    elif has_all_targets:
        return TAG_DUB

    return None


def _find_nfo(movie_path, movie_folder):
    """Find the movie's NFO file."""
    for pattern in ['movie.nfo', f"{movie_folder}.nfo"]:
        potential = os.path.join(movie_path, pattern)
        if os.path.exists(potential):
            return potential
    return None
```

**Step 2: Commit**

```bash
git add taggarr/processors/movies.py
git commit -m "feat: extract movies processor from main.py"
```

---

## Task 12: Wire Up Package Init

**Files:**

- Modify: `taggarr/__init__.py`

**Step 1: Update package init with run functions**

```python
"""Taggarr - Dub Analysis & Tagging."""

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

_logger = None


def run(opts):
    """Run a single scan cycle."""
    global _logger
    if _logger is None:
        _logger = setup_logging()

    _logger.info(f"Taggarr - {__description__}")
    time.sleep(1)
    _logger.info(f"Taggarr - v{__version__} started.")
    time.sleep(1)
    _logger.info("Starting Taggarr scan...")
    time.sleep(5)

    # Log environment
    _logger.debug(f"SONARR_ENABLED={SONARR_ENABLED}, RADARR_ENABLED={RADARR_ENABLED}")
    time.sleep(3)

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

    # Process TV shows
    if SONARR_ENABLED:
        _logger.info("Sonarr enabled - processing TV shows...")
        taggarr_data = json_store.load(TAGGARR_JSON_PATH, key="series")
        taggarr_data = tv.process_all(opts, taggarr_data)
        json_store.save(TAGGARR_JSON_PATH, taggarr_data, key="series")
    else:
        _logger.info("Sonarr not configured - skipping TV shows")

    # Process movies
    if RADARR_ENABLED:
        _logger.info("Radarr enabled - processing movies...")
        taggarr_movies = json_store.load(TAGGARR_MOVIES_JSON_PATH, key="movies")
        taggarr_movies = movies.process_all(opts, taggarr_movies)
        json_store.save(TAGGARR_MOVIES_JSON_PATH, taggarr_movies, key="movies")
    else:
        _logger.info("Radarr not configured - skipping movies")

    _logger.info("Finished Taggarr scan.")
    _logger.info("Check out Huntarr.io to hunt missing dubs!")
    _logger.info(f"Next scan in {RUN_INTERVAL_SECONDS / 3600} hours.")


def run_loop(opts):
    """Run scans continuously at configured interval."""
    while True:
        run(opts)
        time.sleep(RUN_INTERVAL_SECONDS)
```

**Step 2: Commit**

```bash
git add taggarr/__init__.py
git commit -m "feat: wire up package init with run functions"
```

---

## Task 13: Replace main.py with CLI Wrapper

**Files:**

- Replace: `main.py`

**Step 1: Backup original main.py**

```bash
cp main.py main.py.backup
```

**Step 2: Replace main.py with thin CLI wrapper**

```python
#!/usr/bin/env python3
"""Taggarr - Dub Analysis & Tagging CLI."""

import argparse
import time

import taggarr
from taggarr.config import START_RUNNING, WRITE_MODE, RUN_INTERVAL_SECONDS


def main():
    parser = argparse.ArgumentParser(description=taggarr.__description__)
    parser.add_argument(
        '--write-mode', type=int, choices=[0, 1, 2],
        default=WRITE_MODE,
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
    opts = parser.parse_args()

    if START_RUNNING:
        taggarr.run_loop(opts)
    elif any(vars(opts).values()):
        taggarr.run(opts)
    else:
        # Idle mode - wait for external trigger
        while True:
            time.sleep(RUN_INTERVAL_SECONDS)


if __name__ == '__main__':
    main()
```

**Step 3: Commit**

```bash
git add main.py
git commit -m "refactor: replace main.py with thin CLI wrapper"
```

---

## Task 14: Verify and Clean Up

**Step 1: Verify imports work**

```bash
python -c "import taggarr; print(f'v{taggarr.__version__}')"
```

Expected: `v0.5.0`

**Step 2: Verify CLI help works**

```bash
python main.py --help
```

Expected: Help text with description and options

**Step 3: Test dry-run mode (requires env vars)**

```bash
DRY_RUN=true START_RUNNING=false python main.py --dry-run --quick
```

Expected: Runs without errors (may warn about missing config)

**Step 4: Remove backup if tests pass**

```bash
rm main.py.backup
```

**Step 5: Final commit**

```bash
git add -A
git commit -m "chore: complete modular refactor"
```

---

## Task 15: Update Documentation

**Files:**

- Modify: `AGENTS.md` (aka `CLAUDE.md`)

**Step 1: Update CLAUDE.md to reflect new structure**

Change:

```markdown
**Single-file app:** All code lives in `main.py`
```

To:

```markdown
**Package structure:** Code organized in `taggarr/` package:

- `config.py` - Environment variables
- `services/` - Sonarr, Radarr, media analysis
- `storage/` - JSON persistence
- `processors/` - TV and movie scanning logic
- `nfo.py` - NFO file handling
- `languages.py` - Language code utilities
```

**Step 2: Commit**

```bash
git add AGENTS.md
git commit -m "docs: update CLAUDE.md for modular structure"
```

---

## Summary

| Task | Description              | Files                           |
| ---- | ------------------------ | ------------------------------- |
| 1    | Create package structure | `taggarr/` directories          |
| 2    | Extract config           | `taggarr/config.py`             |
| 3    | Extract languages        | `taggarr/languages.py`          |
| 4    | Extract logging          | `taggarr/logging_setup.py`      |
| 5    | Extract media service    | `taggarr/services/media.py`     |
| 6    | Extract Sonarr service   | `taggarr/services/sonarr.py`    |
| 7    | Extract Radarr service   | `taggarr/services/radarr.py`    |
| 8    | Extract JSON storage     | `taggarr/storage/json_store.py` |
| 9    | Extract NFO module       | `taggarr/nfo.py`                |
| 10   | Extract TV processor     | `taggarr/processors/tv.py`      |
| 11   | Extract movies processor | `taggarr/processors/movies.py`  |
| 12   | Wire up package init     | `taggarr/__init__.py`           |
| 13   | Replace main.py          | `main.py`                       |
| 14   | Verify and clean up      | -                               |
| 15   | Update documentation     | `AGENTS.md`                     |

**Total commits:** 15
**Estimated tasks:** 15 (each ~5-10 min)
