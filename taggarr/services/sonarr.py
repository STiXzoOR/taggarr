"""Sonarr API client."""

import os
import time
import logging
from typing import Dict, List, Optional

import requests

logger = logging.getLogger("taggarr")


class SonarrClient:
    """Client for Sonarr API."""

    def __init__(self, url: str, api_key: str):
        self.url = url.rstrip("/")
        self.api_key = api_key
        self._headers = {"X-Api-Key": self.api_key}

    def get_series_by_path(self, path: str) -> Optional[Dict]:
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

    def get_series_id(self, path: str) -> Optional[int]:
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
