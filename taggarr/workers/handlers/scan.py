"""Scan handler for processing media instances."""

import json
import logging
from datetime import datetime, timezone
from typing import Any

from taggarr.workers.handlers.base import BaseHandler

logger = logging.getLogger("taggarr")


class ScanHandler(BaseHandler):
    """Handler for ScanInstance commands."""

    async def execute(self, **kwargs: Any) -> None:
        """Execute a scan for the specified instance.

        Args:
            **kwargs: Must contain 'instance_id' key with the instance ID to scan.

        Raises:
            ValueError: If instance_id is not provided or instance not found.
        """
        instance_id = kwargs.get("instance_id")
        if instance_id is None:
            raise ValueError("instance_id is required for ScanInstance command")

        from taggarr.config_schema import InstanceConfig, TagsConfig
        from taggarr.db import History, Instance, Media, Season, Tag

        with self._session_factory() as db:
            instance = db.query(Instance).filter(Instance.id == instance_id).first()
            if not instance:
                raise ValueError(f"Instance {instance_id} not found")

            if not instance.enabled:
                logger.info(f"Instance {instance.name} is disabled, skipping scan")
                return

            logger.info(f"Starting scan for instance: {instance.name}")

            # Create client based on instance type
            if instance.type == "sonarr":
                await self._scan_sonarr(db, instance)
            elif instance.type == "radarr":
                await self._scan_radarr(db, instance)
            else:
                raise ValueError(f"Unknown instance type: {instance.type}")

            # Record history
            history = History(
                date=datetime.now(timezone.utc),
                event_type="scan",
                instance_id=instance.id,
                data=json.dumps({"instance_name": instance.name}),
            )
            db.add(history)
            db.commit()

            logger.info(f"Completed scan for instance: {instance.name}")

    async def _scan_sonarr(self, db, instance) -> None:
        """Scan a Sonarr instance for TV shows.

        Args:
            db: Database session.
            instance: Instance model object.
        """
        from taggarr.config_schema import InstanceConfig, TagsConfig
        from taggarr.services.sonarr import SonarrClient

        # Parse instance settings
        tags_dict = json.loads(instance.tags) if isinstance(instance.tags, str) else {}
        target_langs = (
            instance.target_languages.split(",")
            if instance.target_languages
            else ["eng"]
        )

        config = InstanceConfig(
            name=instance.name,
            type=instance.type,
            url=instance.url,
            api_key=instance.api_key,
            root_path=instance.root_path,
            target_languages=target_langs,
            tags=TagsConfig(
                dub=tags_dict.get("dub", "dub"),
                semi=tags_dict.get("semi", "semi-dub"),
                wrong=tags_dict.get("wrong", "wrong-dub"),
            ),
            target_genre=instance.target_genre,
            quick_mode=bool(instance.quick_mode),
        )

        client = SonarrClient(config.url, config.api_key)
        logger.info(f"Scanning Sonarr instance: {instance.name}")

        # The actual scanning would use processors.tv.process_all()
        # For now, we just mark this as a placeholder for full integration
        # Full integration would require the opts object from CLI
        logger.info(f"Sonarr scan placeholder for {instance.name}")

    async def _scan_radarr(self, db, instance) -> None:
        """Scan a Radarr instance for movies.

        Args:
            db: Database session.
            instance: Instance model object.
        """
        from taggarr.config_schema import InstanceConfig, TagsConfig
        from taggarr.services.radarr import RadarrClient

        tags_dict = json.loads(instance.tags) if isinstance(instance.tags, str) else {}
        target_langs = (
            instance.target_languages.split(",")
            if instance.target_languages
            else ["eng"]
        )

        config = InstanceConfig(
            name=instance.name,
            type=instance.type,
            url=instance.url,
            api_key=instance.api_key,
            root_path=instance.root_path,
            target_languages=target_langs,
            tags=TagsConfig(
                dub=tags_dict.get("dub", "dub"),
                semi=tags_dict.get("semi", "semi-dub"),
                wrong=tags_dict.get("wrong", "wrong-dub"),
            ),
            target_genre=instance.target_genre,
            quick_mode=bool(instance.quick_mode),
        )

        client = RadarrClient(config.url, config.api_key)
        logger.info(f"Scanning Radarr instance: {instance.name}")

        # The actual scanning would use processors.movies.process_all()
        # For now, we just mark this as a placeholder for full integration
        logger.info(f"Radarr scan placeholder for {instance.name}")
