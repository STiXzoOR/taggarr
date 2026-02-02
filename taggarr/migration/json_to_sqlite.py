"""Migrate JSON storage to SQLite database."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from taggarr.db import Instance, Media, Tag, create_engine, get_session, init_db


def migrate_instances(json_path: Path, db: Session) -> int:
    """Migrate instances from JSON to database.

    Args:
        json_path: Path to the instances JSON file.
        db: SQLAlchemy session to use for database operations.

    Returns:
        Number of instances migrated.
    """
    if not json_path.exists():
        return 0

    with open(json_path) as f:
        data: list[dict[str, Any]] = json.load(f)

    count = 0
    for item in data:
        instance = Instance(
            name=item["name"],
            type=item["type"],
            url=item["url"],
            api_key=item["api_key"],
            root_path=item.get("root_path", ""),
            target_languages=json.dumps(item.get("target_languages", [])),
            tags=json.dumps(item.get("tags", {})),
            target_genre=item.get("target_genre"),
            enabled=1 if item.get("enabled", True) else 0,
            quick_mode=1 if item.get("quick_mode", False) else 0,
            require_original_default=1 if item.get("require_original_default", False) else 0,
            notify_on_wrong_dub=1 if item.get("notify_on_wrong_dub", False) else 0,
            notify_on_original_missing=1 if item.get("notify_on_original_missing", False) else 0,
        )
        db.add(instance)
        count += 1

    return count


def migrate_media(json_path: Path, db: Session) -> int:
    """Migrate media data from JSON to database.

    Args:
        json_path: Path to the media JSON file.
        db: SQLAlchemy session to use for database operations.

    Returns:
        Number of media items migrated.
    """
    if not json_path.exists():
        return 0

    with open(json_path) as f:
        data: list[dict[str, Any]] = json.load(f)

    count = 0
    for item in data:
        # Find tag by label if specified
        tag = None
        if item.get("tag"):
            tag = db.query(Tag).filter(Tag.label == item["tag"]).first()

        # Parse datetime fields
        added = datetime.fromisoformat(item["added"]) if item.get("added") else datetime.now()
        last_scanned = (
            datetime.fromisoformat(item["last_scanned"]) if item.get("last_scanned") else None
        )

        media = Media(
            instance_id=item["instance_id"],
            path=item["path"],
            title=item["title"],
            clean_title=item["clean_title"],
            media_type=item["media_type"],
            original_language=item.get("original_language"),
            tag_id=tag.id if tag else None,
            added=added,
            last_scanned=last_scanned,
            last_modified=item.get("last_modified"),
            override_require_original=item.get("override_require_original"),
            override_notify=item.get("override_notify"),
        )
        db.add(media)
        count += 1

    return count


def run_migration(data_dir: Path, db_path: Path) -> dict[str, int]:
    """Run full migration from JSON files to SQLite.

    Creates the database, initializes tables, and migrates data from
    JSON files in the data directory.

    Args:
        data_dir: Directory containing JSON data files.
        db_path: Path where the SQLite database should be created.

    Returns:
        Dictionary with counts of migrated items by type.
    """
    engine = create_engine(f"sqlite:///{db_path}")
    init_db(engine)

    with get_session(engine) as db:
        results = {
            "instances": migrate_instances(data_dir / "instances.json", db),
            "media": migrate_media(data_dir / "media.json", db),
        }

    return results
