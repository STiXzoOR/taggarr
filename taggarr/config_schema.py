"""Configuration data classes."""

from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional


@dataclass
class TagsConfig:
    """Tag name configuration."""
    dub: str = "dub"
    semi: str = "semi-dub"
    wrong: str = "wrong-dub"


@dataclass
class DefaultsConfig:
    """Default settings applied to all instances."""
    target_languages: List[str] = field(default_factory=lambda: ["en"])
    tags: TagsConfig = field(default_factory=TagsConfig)
    dry_run: bool = False
    quick_mode: bool = False
    run_interval_seconds: int = 7200
    log_level: str = "INFO"
    log_path: str = "/logs"


@dataclass
class InstanceConfig:
    """Configuration for a single Sonarr/Radarr instance."""
    name: str
    type: Literal["sonarr", "radarr"]
    url: str
    api_key: str
    root_path: str
    target_languages: List[str] = field(default_factory=list)
    tags: TagsConfig = field(default_factory=TagsConfig)
    dry_run: bool = False
    quick_mode: bool = False
    target_genre: Optional[str] = None


@dataclass
class Config:
    """Top-level configuration."""
    defaults: DefaultsConfig
    instances: Dict[str, InstanceConfig]
