"""Migrate YAML config to database."""

from pathlib import Path
from typing import Any

import yaml
from sqlalchemy.orm import Session

from taggarr.db import Config


def flatten_dict(d: dict[str, Any], prefix: str = "") -> dict[str, str]:
    """Flatten nested dict to dot-notation keys.

    Converts nested dictionaries into a flat dictionary with dot-notation
    keys representing the hierarchy.

    Args:
        d: Nested dictionary to flatten.
        prefix: Current key prefix for recursion.

    Returns:
        Flattened dictionary with dot-notation keys.

    Example:
        >>> flatten_dict({"a": {"b": "value"}})
        {"a.b": "value"}
    """
    items: dict[str, str] = {}
    for k, v in d.items():
        key = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            items.update(flatten_dict(v, key))
        else:
            items[key] = str(v)
    return items


def migrate_config(yaml_path: Path, db: Session) -> int:
    """Migrate YAML config to database Config table.

    Reads configuration from a YAML file and stores it in the database
    Config table. Server configuration is skipped as it must remain in
    YAML for startup.

    Args:
        yaml_path: Path to the YAML configuration file.
        db: SQLAlchemy session to use for database operations.

    Returns:
        Number of configuration items migrated.
    """
    if not yaml_path.exists():
        return 0

    with open(yaml_path) as f:
        data = yaml.safe_load(f) or {}

    count = 0

    flat_config = flatten_dict(data)

    for key, value in flat_config.items():
        # Skip server config (stays in YAML for startup)
        if key.startswith("server."):
            continue

        existing = db.query(Config).filter(Config.key == key).first()
        if existing:
            existing.value = value
        else:
            db.add(Config(key=key, value=value))
        count += 1

    return count
