"""Tests for taggarr.db.migrations module."""

from pathlib import Path

from sqlalchemy import inspect, text

from taggarr.db.database import create_engine, get_session
from taggarr.db.migrations import init_db
from taggarr.db.models import Tag


class TestInitDb:
    """Tests for init_db function."""

    def test_init_db_creates_all_tables(self, tmp_path: Path) -> None:
        """init_db should create all required tables."""
        db_path = tmp_path / "test.db"
        url = f"sqlite:///{db_path}"
        engine = create_engine(url)

        init_db(engine)

        inspector = inspect(engine)
        tables = inspector.get_table_names()

        expected_tables = [
            "users",
            "sessions",
            "api_keys",
            "config",
            "instances",
            "tags",
            "media",
            "seasons",
            "history",
            "notifications",
            "notification_status",
            "commands",
            "scheduled_tasks",
            "backups",
        ]

        for table in expected_tables:
            assert table in tables, f"Table '{table}' was not created"

    def test_init_db_creates_default_tags(self, tmp_path: Path) -> None:
        """init_db should create default dub tags (dub, semi-dub, wrong-dub)."""
        db_path = tmp_path / "test.db"
        url = f"sqlite:///{db_path}"
        engine = create_engine(url)

        init_db(engine)

        with get_session(engine) as session:
            tags = session.query(Tag).all()
            tag_labels = [tag.label for tag in tags]

            assert "dub" in tag_labels
            assert "semi-dub" in tag_labels
            assert "wrong-dub" in tag_labels
            assert len(tags) == 3

    def test_init_db_idempotent(self, tmp_path: Path) -> None:
        """init_db should be idempotent - calling it twice should not error."""
        db_path = tmp_path / "test.db"
        url = f"sqlite:///{db_path}"
        engine = create_engine(url)

        # Call init_db twice
        init_db(engine)
        init_db(engine)

        # Verify tags are not duplicated
        with get_session(engine) as session:
            tags = session.query(Tag).all()
            assert len(tags) == 3

    def test_init_db_preserves_existing_data(self, tmp_path: Path) -> None:
        """init_db should preserve existing data in tables."""
        db_path = tmp_path / "test.db"
        url = f"sqlite:///{db_path}"
        engine = create_engine(url)

        # First init
        init_db(engine)

        # Add custom tag
        with get_session(engine) as session:
            custom_tag = Tag(label="custom-tag")
            session.add(custom_tag)

        # Second init
        init_db(engine)

        # Verify custom tag still exists
        with get_session(engine) as session:
            tags = session.query(Tag).all()
            tag_labels = [tag.label for tag in tags]
            assert "custom-tag" in tag_labels
            assert len(tags) == 4  # 3 default + 1 custom
