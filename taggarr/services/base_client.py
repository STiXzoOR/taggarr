"""Base client for *arr API services (Sonarr, Radarr)."""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from taggarr.exceptions import ApiTransientError, ApiPermanentError

logger = logging.getLogger("taggarr")


class BaseArrClient:
    """Shared functionality for Sonarr/Radarr API clients."""

    # Subclasses set these
    _media_endpoint: str = ""       # e.g. "/api/v3/series" or "/api/v3/movie"
    _media_id_field: str = "id"     # field name for entity ID
    _service_name: str = "arr"      # for log messages

    def __init__(self, url: str, api_key: str) -> None:
        self.url = url.rstrip("/")
        self.api_key = api_key
        self._headers = {"X-Api-Key": self.api_key}
        self._media_cache: Optional[List[Dict]] = None
        self._tag_cache: Optional[List[Dict]] = None

    @retry(
        retry=retry_if_exception_type(ApiTransientError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs,
    ) -> requests.Response:
        """Make an API request with timeout and automatic retry.

        Retries up to 3 times on transient errors (5xx, timeouts,
        connection failures) with exponential backoff.
        Raises ApiTransientError for retryable failures and
        ApiPermanentError for permanent ones.
        """
        kwargs.setdefault("timeout", 30)
        kwargs.setdefault("headers", self._headers)
        url = f"{self.url}{endpoint}"

        try:
            resp = requests.request(method, url, **kwargs)
            resp.raise_for_status()
            return resp
        except requests.ConnectionError as exc:
            raise ApiTransientError(f"{self._service_name} connection failed: {exc}") from exc
        except requests.Timeout as exc:
            raise ApiTransientError(f"{self._service_name} request timed out: {exc}") from exc
        except requests.HTTPError as exc:
            if exc.response is not None and exc.response.status_code >= 500:
                raise ApiTransientError(
                    f"{self._service_name} server error {exc.response.status_code}: {exc}"
                ) from exc
            raise ApiPermanentError(
                f"{self._service_name} client error: {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Tag helpers
    # ------------------------------------------------------------------

    def get_tags(self) -> List[Dict]:
        """Fetch all tags, using cache if available."""
        if self._tag_cache is not None:
            return self._tag_cache
        try:
            resp = self._request("GET", "/api/v3/tag")
            self._tag_cache = resp.json()
        except (ApiTransientError, ApiPermanentError) as exc:
            logger.warning(f"Failed to fetch {self._service_name} tags: {exc}")
            return []
        return self._tag_cache

    def _get_tag_id(self, tag: str) -> Optional[int]:
        """Get tag ID by label (case-insensitive)."""
        for t in self.get_tags():
            if t["label"].lower() == tag.lower():
                return t["id"]
        return None

    def _get_or_create_tag(self, tag: str) -> int:
        """Get existing tag ID or create a new one."""
        tag_id = self._get_tag_id(tag)
        if tag_id is not None:
            return tag_id
        try:
            resp = self._request("POST", "/api/v3/tag", json={"label": tag})
            new_tag = resp.json()
            tag_id = new_tag["id"]
            logger.debug(f"Created new {self._service_name} tag '{tag}' with ID {tag_id}")
            # Invalidate tag cache so new tag is visible
            self._tag_cache = None
            return tag_id
        except (ApiTransientError, ApiPermanentError) as exc:
            raise ApiPermanentError(f"Failed to create tag '{tag}': {exc}") from exc

    # ------------------------------------------------------------------
    # Media list cache
    # ------------------------------------------------------------------

    def _fetch_media_list(self) -> List[Dict]:
        """Fetch the full media list, using cache if available."""
        if self._media_cache is not None:
            return self._media_cache
        try:
            resp = self._request("GET", self._media_endpoint)
            self._media_cache = resp.json()
        except (ApiTransientError, ApiPermanentError) as exc:
            logger.warning(f"Failed to fetch {self._service_name} media list: {exc}")
            return []
        return self._media_cache

    def clear_cache(self) -> None:
        """Clear cached data. Call at the start of each scan cycle."""
        self._media_cache = None
        self._tag_cache = None

    # ------------------------------------------------------------------
    # Atomic tag operations
    # ------------------------------------------------------------------

    def apply_tag_changes(
        self,
        media_id: int,
        add_tags: Optional[List[str]] = None,
        remove_tags: Optional[List[str]] = None,
        dry_run: bool = False,
    ) -> None:
        """Apply tag changes atomically: single GET, modify, single PUT.

        Collects all tag IDs to add/remove, then does one GET of the media
        item, modifies its tag list, and one PUT back.
        """
        add_tags = add_tags or []
        remove_tags = remove_tags or []

        if not add_tags and not remove_tags:
            return

        if dry_run:
            if add_tags:
                logger.info(f"[Dry Run] Would add tags {add_tags} to {self._service_name} {media_id}")
            if remove_tags:
                logger.info(f"[Dry Run] Would remove tags {remove_tags} from {self._service_name} {media_id}")
            return

        # Resolve tag names to IDs
        add_ids = set()
        for tag in add_tags:
            add_ids.add(self._get_or_create_tag(tag))

        remove_ids = set()
        for tag in remove_tags:
            tid = self._get_tag_id(tag)
            if tid is not None:
                remove_ids.add(tid)

        if not add_ids and not remove_ids:
            return

        # Single GET
        item_endpoint = f"{self._media_endpoint}/{media_id}"
        resp = self._request("GET", item_endpoint)
        item_data = resp.json()

        # Modify tags
        current_tags = set(item_data.get("tags", []))
        new_tags = (current_tags | add_ids) - remove_ids

        if new_tags == current_tags:
            logger.debug(f"No tag changes needed for {self._service_name} {media_id}")
            return

        item_data["tags"] = sorted(new_tags)

        # Log changes
        added = add_ids - current_tags
        removed = remove_ids & current_tags
        if added:
            logger.debug(f"Adding tag IDs {added} to {self._service_name} {media_id}")
        if removed:
            logger.debug(f"Removing tag IDs {removed} from {self._service_name} {media_id}")

        # Single PUT
        self._request("PUT", item_endpoint, json=item_data)

    # ------------------------------------------------------------------
    # Legacy wrappers (kept for backwards compatibility during transition)
    # ------------------------------------------------------------------

    def add_tag(self, media_id: int, tag: str, dry_run: bool = False) -> None:
        """Add a single tag. Delegates to apply_tag_changes."""
        self.apply_tag_changes(media_id, add_tags=[tag], dry_run=dry_run)

    def remove_tag(self, media_id: int, tag: str, dry_run: bool = False) -> None:
        """Remove a single tag. Delegates to apply_tag_changes."""
        self.apply_tag_changes(media_id, remove_tags=[tag], dry_run=dry_run)
