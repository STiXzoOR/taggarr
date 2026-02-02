"""Database initialization and migrations."""

from sqlalchemy import Engine

from taggarr.db.database import get_session
from taggarr.db.models import Base, Tag


def init_db(engine: Engine) -> None:
    """Initialize the database by creating all tables and seeding default data.

    This function creates all tables defined in the SQLAlchemy models if they
    don't exist, and seeds the default tags (dub, semi-dub, wrong-dub).

    The function is idempotent - calling it multiple times will not create
    duplicate data or raise errors.

    Args:
        engine: SQLAlchemy Engine instance to use for database operations.
    """
    # Create all tables
    Base.metadata.create_all(engine)

    # Seed default tags
    default_tags = ["dub", "semi-dub", "wrong-dub"]

    with get_session(engine) as session:
        for label in default_tags:
            existing = session.query(Tag).filter_by(label=label).first()
            if existing is None:
                tag = Tag(label=label)
                session.add(tag)
