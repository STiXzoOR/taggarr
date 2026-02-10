"""Radarr API client."""

from __future__ import annotations

import os
import logging
from typing import Dict, List, Optional

from taggarr.services.base_client import BaseArrClient

logger = logging.getLogger("taggarr")


class RadarrClient(BaseArrClient):
    """Client for Radarr API."""

    _media_endpoint = "/api/v3/movie"
    _service_name = "Radarr"

    def get_movies(self) -> List[Dict]:
        """Fetch all movies from Radarr API."""
        return self._fetch_media_list()

    def get_movie_by_path(self, path: str) -> Optional[Dict]:
        """Find a specific movie by its folder path.

        Matches by full path first, falls back to basename.
        """
        media_list = self._fetch_media_list()

        # Full path match first
        for m in media_list:
            if m.get("path") == path:
                return m

        # Basename fallback
        target_basename = os.path.basename(path)
        for m in media_list:
            if os.path.basename(m.get("path", "")) == target_basename:
                return m

        return None
