"""Sonarr API client."""

from __future__ import annotations

import os
import logging
from typing import Dict, Optional

from taggarr.exceptions import ApiTransientError, ApiPermanentError
from taggarr.services.base_client import BaseArrClient

logger = logging.getLogger("taggarr")


class SonarrClient(BaseArrClient):
    """Client for Sonarr API."""

    _media_endpoint = "/api/v3/series"
    _service_name = "Sonarr"

    def get_series_by_path(self, path: str) -> Optional[Dict]:
        """Find series by folder path.

        Matches by full path first, falls back to basename.
        """
        media_list = self._fetch_media_list()

        # Full path match first
        for s in media_list:
            if s.get("path") == path:
                return s

        # Basename fallback
        target_basename = os.path.basename(path)
        for s in media_list:
            if os.path.basename(s.get("path", "")) == target_basename:
                return s

        return None

    def get_series_id(self, path: str) -> Optional[int]:
        """Get just the series ID."""
        series = self.get_series_by_path(path)
        return series["id"] if series else None

    def refresh_series(self, series_id: int, dry_run: bool = False) -> None:
        """Trigger a series refresh in Sonarr."""
        if dry_run:
            logger.info(f"[Dry Run] Would trigger refresh for series {series_id}")
            return
        try:
            payload = {"name": "RefreshSeries", "seriesId": series_id}
            self._request("POST", "/api/v3/command", json=payload, timeout=10)
            logger.debug(f"Sonarr refresh triggered for series ID: {series_id}")
        except (ApiTransientError, ApiPermanentError) as exc:
            logger.warning(f"Failed to trigger Sonarr refresh: {exc}")
