"""Movie scanning and tagging processor."""

import os
import logging
from datetime import datetime
from typing import Dict, Optional

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
                language_codes: set) -> Optional[Dict]:
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
                   language_codes: set) -> Optional[str]:
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


def _find_nfo(movie_path: str, movie_folder: str) -> Optional[str]:
    """Find the movie's NFO file."""
    for pattern in ['movie.nfo', f"{movie_folder}.nfo"]:
        potential = os.path.join(movie_path, pattern)
        if os.path.exists(potential):
            return potential
    return None
