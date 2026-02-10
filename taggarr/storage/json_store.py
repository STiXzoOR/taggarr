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
    except (json.JSONDecodeError, OSError, KeyError, ValueError) as e:
        logger.warning(f"taggarr.json is corrupted: {e}")
        backup_path = json_path + ".bak"
        os.rename(json_path, backup_path)
        logger.warning(f"Corrupted file moved to: {backup_path}")
        return {key: {}}


def save(json_path, data, key="series"):
    """Save taggarr.json with compacted formatting.

    Uses write-to-temp-then-rename to avoid partial writes on crash.
    """
    if not json_path:
        return

    try:
        data["version"] = __version__
        ordered = {"version": __version__}
        ordered.update({k: v for k, v in data.items() if k != "version"})

        raw_json = json.dumps(ordered, indent=2, ensure_ascii=False)
        compact_json = _compact_lists(raw_json)

        tmp_path = json_path + ".tmp"
        with open(tmp_path, 'w') as f:
            f.write(compact_json)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, json_path)
        logger.debug("taggarr.json saved successfully.")
    except (OSError, TypeError, ValueError) as e:
        logger.warning(f"Failed to save taggarr.json: {e}")


def cleanup_orphans(data, key, valid_paths):
    """Remove entries whose paths no longer exist on disk.

    Args:
        data: The taggarr data dict (e.g. {"series": {...}} or {"movies": {...}})
        key: The top-level key ("series" or "movies")
        valid_paths: Set of paths that currently exist

    Returns:
        Number of orphaned entries removed.
    """
    entries = data.get(key, {})
    orphans = [path for path in entries if path not in valid_paths]
    for path in orphans:
        logger.info(f"Removing orphaned entry: {path}")
        del entries[path]
    return len(orphans)


def cleanup_orphans_for_root(data, key, root_path):
    """Gather current paths from root_path and remove orphaned entries.

    Wraps os.listdir in error handling so a temporary mount failure
    does not prevent the caller from saving scan progress.

    Returns:
        Number of orphaned entries removed, or 0 if listing failed.
    """
    try:
        current_paths = set()
        for entry in os.listdir(root_path):
            path = os.path.abspath(os.path.join(root_path, entry))
            if os.path.isdir(path):
                current_paths.add(path)
    except OSError as e:
        logger.warning(f"Could not list {root_path} for orphan cleanup: {e}")
        return 0
    return cleanup_orphans(data, key, current_paths)


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
