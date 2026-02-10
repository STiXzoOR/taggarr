"""Tests for taggarr.migration module."""

import json
from pathlib import Path

import pytest
import yaml

from taggarr.db.database import create_engine, get_session
from taggarr.db.migrations import init_db
from taggarr.db.models import Config, Instance, Media, Tag
from taggarr.migration.config_migration import flatten_dict, migrate_config
from taggarr.migration.json_to_sqlite import (
    migrate_instances,
    migrate_media,
    run_migration,
)


class TestMigrateInstances:
    """Tests for migrate_instances function."""

    def test_migrate_instances_from_json(self, tmp_path: Path) -> None:
        """migrate_instances should migrate JSON data to database."""
        # Setup: Create JSON file with instance data
        instances_data = [
            {
                "name": "sonarr-main",
                "type": "sonarr",
                "url": "http://localhost:8989",
                "api_key": "test-api-key",
                "root_path": "/media/tv",
                "target_languages": ["en", "de"],
                "tags": {"dub": "dub-tag", "semi": "semi-tag", "wrong": "wrong-tag"},
                "enabled": True,
                "quick_mode": False,
                "target_genre": "Drama",
                "require_original_default": True,
                "notify_on_wrong_dub": True,
                "notify_on_original_missing": False,
            },
            {
                "name": "radarr-main",
                "type": "radarr",
                "url": "http://localhost:7878",
                "api_key": "test-api-key-2",
                "root_path": "/media/movies",
                "target_languages": ["en"],
                "tags": {"dub": "dubbed"},
                "enabled": False,
                "quick_mode": True,
            },
        ]

        json_path = tmp_path / "instances.json"
        with open(json_path, "w") as f:
            json.dump(instances_data, f)

        # Setup: Create database
        db_path = tmp_path / "test.db"
        url = f"sqlite:///{db_path}"
        engine = create_engine(url)
        init_db(engine)

        # Execute
        with get_session(engine) as session:
            count = migrate_instances(json_path, session)

        # Verify
        assert count == 2

        with get_session(engine) as session:
            instances = session.query(Instance).all()
            assert len(instances) == 2

            sonarr = session.query(Instance).filter_by(name="sonarr-main").first()
            assert sonarr is not None
            assert sonarr.type == "sonarr"
            assert sonarr.url == "http://localhost:8989"
            assert sonarr.api_key == "test-api-key"
            assert sonarr.root_path == "/media/tv"
            assert json.loads(sonarr.target_languages) == ["en", "de"]
            assert sonarr.enabled == 1
            assert sonarr.quick_mode == 0
            assert sonarr.target_genre == "Drama"
            assert sonarr.require_original_default == 1
            assert sonarr.notify_on_wrong_dub == 1
            assert sonarr.notify_on_original_missing == 0

            radarr = session.query(Instance).filter_by(name="radarr-main").first()
            assert radarr is not None
            assert radarr.enabled == 0
            assert radarr.quick_mode == 1

    def test_migrate_instances_handles_missing_file(self, tmp_path: Path) -> None:
        """migrate_instances should return 0 for missing file."""
        # Setup
        json_path = tmp_path / "nonexistent.json"
        db_path = tmp_path / "test.db"
        url = f"sqlite:///{db_path}"
        engine = create_engine(url)
        init_db(engine)

        # Execute
        with get_session(engine) as session:
            count = migrate_instances(json_path, session)

        # Verify
        assert count == 0

    def test_migrate_instances_handles_defaults(self, tmp_path: Path) -> None:
        """migrate_instances should use defaults for missing optional fields."""
        instances_data = [
            {
                "name": "minimal-instance",
                "type": "sonarr",
                "url": "http://localhost:8989",
                "api_key": "test-key",
            },
        ]

        json_path = tmp_path / "instances.json"
        with open(json_path, "w") as f:
            json.dump(instances_data, f)

        db_path = tmp_path / "test.db"
        url = f"sqlite:///{db_path}"
        engine = create_engine(url)
        init_db(engine)

        with get_session(engine) as session:
            count = migrate_instances(json_path, session)

        assert count == 1

        with get_session(engine) as session:
            instance = session.query(Instance).first()
            assert instance.root_path == ""
            assert json.loads(instance.target_languages) == []
            assert instance.enabled == 1
            assert instance.quick_mode == 0


class TestMigrateMedia:
    """Tests for migrate_media function."""

    def test_migrate_media_from_json(self, tmp_path: Path) -> None:
        """migrate_media should migrate JSON data to database."""
        # Setup: Create database with instance first
        db_path = tmp_path / "test.db"
        url = f"sqlite:///{db_path}"
        engine = create_engine(url)
        init_db(engine)

        # Create an instance for foreign key
        with get_session(engine) as session:
            instance = Instance(
                name="test-instance",
                type="sonarr",
                url="http://localhost:8989",
                api_key="test-key",
                root_path="/media/tv",
                target_languages="[]",
                tags="{}",
                enabled=1,
                quick_mode=0,
                require_original_default=0,
                notify_on_wrong_dub=0,
                notify_on_original_missing=0,
            )
            session.add(instance)
            session.flush()
            instance_id = instance.id

        # Setup: Create JSON file with media data
        media_data = [
            {
                "instance_id": instance_id,
                "path": "/media/tv/Breaking Bad",
                "title": "Breaking Bad",
                "clean_title": "breakingbad",
                "media_type": "series",
                "original_language": "en",
                "tag": "dub",
                "added": "2024-01-15T10:30:00",
                "last_scanned": "2024-06-01T15:00:00",
                "last_modified": 1717250400,
            },
            {
                "instance_id": instance_id,
                "path": "/media/tv/Game of Thrones",
                "title": "Game of Thrones",
                "clean_title": "gameofthrones",
                "media_type": "series",
                "original_language": "en",
                "tag": None,
                "added": "2024-02-20T08:00:00",
            },
        ]

        json_path = tmp_path / "media.json"
        with open(json_path, "w") as f:
            json.dump(media_data, f)

        # Execute
        with get_session(engine) as session:
            count = migrate_media(json_path, session)

        # Verify
        assert count == 2

        with get_session(engine) as session:
            media_list = session.query(Media).all()
            assert len(media_list) == 2

            bb = session.query(Media).filter_by(title="Breaking Bad").first()
            assert bb is not None
            assert bb.path == "/media/tv/Breaking Bad"
            assert bb.clean_title == "breakingbad"
            assert bb.media_type == "series"
            assert bb.original_language == "en"
            assert bb.tag is not None
            assert bb.tag.label == "dub"
            assert bb.last_modified == 1717250400

            got = session.query(Media).filter_by(title="Game of Thrones").first()
            assert got is not None
            assert got.tag is None

    def test_migrate_media_handles_missing_file(self, tmp_path: Path) -> None:
        """migrate_media should return 0 for missing file."""
        json_path = tmp_path / "nonexistent.json"
        db_path = tmp_path / "test.db"
        url = f"sqlite:///{db_path}"
        engine = create_engine(url)
        init_db(engine)

        with get_session(engine) as session:
            count = migrate_media(json_path, session)

        assert count == 0


class TestMigrateConfig:
    """Tests for migrate_config function."""

    def test_migrate_config_from_yaml(self, tmp_path: Path) -> None:
        """migrate_config should migrate YAML config to database."""
        # Setup: Create YAML config file
        config_data = {
            "defaults": {
                "target_languages": ["en", "de"],
                "dry_run": False,
                "quick_mode": True,
                "run_interval_seconds": 3600,
                "log_level": "DEBUG",
            },
            "server": {
                "host": "0.0.0.0",
                "port": 8080,
            },
        }

        yaml_path = tmp_path / "config.yaml"
        with open(yaml_path, "w") as f:
            yaml.dump(config_data, f)

        db_path = tmp_path / "test.db"
        url = f"sqlite:///{db_path}"
        engine = create_engine(url)
        init_db(engine)

        # Execute
        with get_session(engine) as session:
            count = migrate_config(yaml_path, session)

        # Verify: Server config should be skipped
        assert count == 5  # 5 defaults, 0 server (skipped)

        with get_session(engine) as session:
            configs = session.query(Config).all()
            config_keys = [c.key for c in configs]

            # Defaults should be migrated
            assert "defaults.target_languages" in config_keys
            assert "defaults.dry_run" in config_keys
            assert "defaults.quick_mode" in config_keys
            assert "defaults.run_interval_seconds" in config_keys
            assert "defaults.log_level" in config_keys

            # Server config should be skipped
            assert "server.host" not in config_keys
            assert "server.port" not in config_keys

            # Check values
            dry_run = session.query(Config).filter_by(key="defaults.dry_run").first()
            assert dry_run.value == "False"

            quick_mode = session.query(Config).filter_by(key="defaults.quick_mode").first()
            assert quick_mode.value == "True"

    def test_migrate_config_handles_missing_file(self, tmp_path: Path) -> None:
        """migrate_config should return 0 for missing file."""
        yaml_path = tmp_path / "nonexistent.yaml"
        db_path = tmp_path / "test.db"
        url = f"sqlite:///{db_path}"
        engine = create_engine(url)
        init_db(engine)

        with get_session(engine) as session:
            count = migrate_config(yaml_path, session)

        assert count == 0

    def test_migrate_config_updates_existing(self, tmp_path: Path) -> None:
        """migrate_config should update existing config values."""
        # Setup: Create database with existing config
        db_path = tmp_path / "test.db"
        url = f"sqlite:///{db_path}"
        engine = create_engine(url)
        init_db(engine)

        with get_session(engine) as session:
            session.add(Config(key="defaults.log_level", value="INFO"))

        # Setup: Create YAML with updated value
        config_data = {
            "defaults": {
                "log_level": "DEBUG",
            },
        }

        yaml_path = tmp_path / "config.yaml"
        with open(yaml_path, "w") as f:
            yaml.dump(config_data, f)

        # Execute
        with get_session(engine) as session:
            count = migrate_config(yaml_path, session)

        # Verify
        assert count == 1

        with get_session(engine) as session:
            config = session.query(Config).filter_by(key="defaults.log_level").first()
            assert config.value == "DEBUG"


class TestFlattenDict:
    """Tests for flatten_dict helper function."""

    def test_flatten_config_dict(self) -> None:
        """flatten_dict should flatten nested dicts to dot-notation keys."""
        nested = {
            "level1": {
                "level2a": "value1",
                "level2b": {
                    "level3": "value2",
                },
            },
            "top_level": "value3",
        }

        result = flatten_dict(nested)

        assert result == {
            "level1.level2a": "value1",
            "level1.level2b.level3": "value2",
            "top_level": "value3",
        }

    def test_flatten_dict_empty(self) -> None:
        """flatten_dict should return empty dict for empty input."""
        result = flatten_dict({})
        assert result == {}

    def test_flatten_dict_single_level(self) -> None:
        """flatten_dict should work with single-level dicts."""
        flat = {"key1": "val1", "key2": "val2"}
        result = flatten_dict(flat)
        assert result == {"key1": "val1", "key2": "val2"}


class TestRunMigration:
    """Tests for run_migration function."""

    def test_run_migration_full(self, tmp_path: Path) -> None:
        """run_migration should migrate all data files."""
        # Setup: Create data directory with JSON files
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        instances_data = [
            {
                "name": "sonarr",
                "type": "sonarr",
                "url": "http://localhost:8989",
                "api_key": "test-key",
                "root_path": "/media/tv",
                "target_languages": ["en"],
                "tags": {},
                "enabled": True,
                "quick_mode": False,
            },
        ]

        with open(data_dir / "instances.json", "w") as f:
            json.dump(instances_data, f)

        # Execute
        db_path = tmp_path / "taggarr.db"
        results = run_migration(data_dir, db_path)

        # Verify
        assert results["instances"] == 1
        assert results["media"] == 0  # No media.json file

        # Verify database has data
        engine = create_engine(f"sqlite:///{db_path}")
        with get_session(engine) as session:
            instances = session.query(Instance).all()
            assert len(instances) == 1

    def test_run_migration_empty_directory(self, tmp_path: Path) -> None:
        """run_migration should handle empty data directory."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        db_path = tmp_path / "taggarr.db"
        results = run_migration(data_dir, db_path)

        assert results["instances"] == 0
        assert results["media"] == 0

    def test_migration_handles_missing_files(self, tmp_path: Path) -> None:
        """Migration should gracefully handle missing data files."""
        data_dir = tmp_path / "empty_data"
        data_dir.mkdir()

        db_path = tmp_path / "taggarr.db"
        results = run_migration(data_dir, db_path)

        # Should not raise, should return zeros
        assert results["instances"] == 0
        assert results["media"] == 0
