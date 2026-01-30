"""Radarr API client."""

import os
import time
import logging
from typing import Dict, List, Optional

import requests

logger = logging.getLogger("taggarr")


class RadarrClient:
    """Client for Radarr API."""

    def __init__(self, url: str, api_key: str):
        self.url = url.rstrip("/")
        self.api_key = api_key
        self._headers = {"X-Api-Key": self.api_key}

    def get_movies(self) -> List[Dict]:
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

    def get_movie_by_path(self, path: str) -> Optional[Dict]:
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

    def _get_tag_id(self, tag: str) -> Optional[int]:
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
