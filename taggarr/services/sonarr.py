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
