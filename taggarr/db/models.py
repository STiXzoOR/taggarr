"""SQLAlchemy models for taggarr."""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


class User(Base):
    """User account for authentication."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    identifier: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    username: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String, nullable=False)
    salt: Mapped[str] = mapped_column(String, nullable=False)
    iterations: Mapped[int] = mapped_column(Integer, nullable=False)

    sessions: Mapped[list["SessionModel"]] = relationship(
        "SessionModel", back_populates="user"
    )


class SessionModel(Base):
    """User session for authentication."""

    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    identifier: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="sessions")


class ApiKey(Base):
    """API key for programmatic access."""

    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    label: Mapped[str] = mapped_column(String, nullable=False)
    key: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class Config(Base):
    """Key-value configuration storage."""

    __tablename__ = "config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    value: Mapped[str] = mapped_column(String, nullable=False)


class Instance(Base):
    """Sonarr/Radarr instance configuration."""

    __tablename__ = "instances"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)
    url: Mapped[str] = mapped_column(String, nullable=False)
    api_key: Mapped[str] = mapped_column(String, nullable=False)
    root_path: Mapped[str] = mapped_column(String, nullable=False)
    target_languages: Mapped[str] = mapped_column(String, nullable=False)
    tags: Mapped[str] = mapped_column(String, nullable=False)
    target_genre: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    quick_mode: Mapped[int] = mapped_column(Integer, nullable=False)
    enabled: Mapped[int] = mapped_column(Integer, nullable=False)
    require_original_default: Mapped[int] = mapped_column(Integer, nullable=False)
    notify_on_wrong_dub: Mapped[int] = mapped_column(Integer, nullable=False)
    notify_on_original_missing: Mapped[int] = mapped_column(Integer, nullable=False)

    media: Mapped[list["Media"]] = relationship("Media", back_populates="instance")


class Tag(Base):
    """Tag for categorizing media (dub, semi-dub, wrong-dub)."""

    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    label: Mapped[str] = mapped_column(String, unique=True, nullable=False)

    media: Mapped[list["Media"]] = relationship("Media", back_populates="tag")


class Media(Base):
    """Media item (TV show or movie) tracked by taggarr."""

    __tablename__ = "media"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    instance_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("instances.id"), nullable=False
    )
    path: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    clean_title: Mapped[str] = mapped_column(String, nullable=False)
    media_type: Mapped[str] = mapped_column(String, nullable=False)
    original_language: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    tag_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("tags.id"), nullable=True
    )
    added: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    last_scanned: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_modified: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    override_require_original: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )
    override_notify: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    instance: Mapped["Instance"] = relationship("Instance", back_populates="media")
    tag: Mapped[Optional["Tag"]] = relationship("Tag", back_populates="media")
    seasons: Mapped[list["Season"]] = relationship("Season", back_populates="media")


class Season(Base):
    """Season data for TV shows."""

    __tablename__ = "seasons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    media_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("media.id"), nullable=False
    )
    season_number: Mapped[int] = mapped_column(Integer, nullable=False)
    episode_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    original_dub: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    dub: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    missing_dub: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    unexpected_languages: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    last_modified: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    media: Mapped["Media"] = relationship("Media", back_populates="seasons")
