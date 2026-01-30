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
