"""TV show scanning and tagging processor."""

from __future__ import annotations

import os
import re
import logging
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple

from taggarr.config_schema import InstanceConfig
from taggarr.services.sonarr import SonarrClient
from taggarr.services import media
from taggarr.storage import json_store
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
            all_tags = [instance.tags.dub, instance.tags.semi, instance.tags.wrong]
            client.apply_tag_changes(series_id, remove_tags=all_tags, dry_run=dry_run)
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

    # Cleanup orphaned entries
    current_paths = set()
    for entry in os.listdir(instance.root_path):
        path = os.path.abspath(os.path.join(instance.root_path, entry))
        if os.path.isdir(path):
            current_paths.add(path)
    removed = json_store.cleanup_orphans(taggarr_data, "series", current_paths)
    if removed:
        logger.info(f"Cleaned up {removed} orphaned series entries")

    return taggarr_data


def _scan_show(show_path: str, series_meta: dict, instance: InstanceConfig,
               language_codes: set, quick: bool = False) -> Tuple[Optional[str], dict]:
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


def _passes_genre_filter(nfo_path: str, target_genre: Optional[str]) -> bool:
    """Check if show passes genre filter."""
    if not target_genre:
        return True
    genres = nfo.get_genres(nfo_path)
    return target_genre.lower() in genres


def _apply_tags(client: SonarrClient, series_id: int, tag: Optional[str],
                instance: InstanceConfig, dry_run: bool) -> None:
    """Apply appropriate tags and remove conflicting ones atomically."""
    all_tags = [instance.tags.dub, instance.tags.semi, instance.tags.wrong]

    if tag:
        add_tags = [tag]
        remove_tags = [t for t in all_tags if t != tag]
    else:
        logger.info("Removing all tags since it's original (no tag)")
        add_tags = []
        remove_tags = all_tags

    client.apply_tag_changes(series_id, add_tags=add_tags, remove_tags=remove_tags, dry_run=dry_run)


def _determine_status(stats: dict) -> str:
    """Determine season status from stats."""
    if stats["unexpected_languages"]:
        return "wrong-dub"
    elif not stats["missing_dub"] and stats["dub"]:
        return "fully-dub"
    elif stats["dub"]:
        return "semi-dub"
    return "original"


def _build_entry(show_folder: str, tag: Optional[str], seasons: dict,
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
        "last_scan": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "original_language": original_lang,
        "seasons": seasons,
        "last_modified": mtime,
    }
