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
