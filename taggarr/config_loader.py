"""YAML configuration loader with env var interpolation."""

import os
import re
import yaml
from pathlib import Path
from typing import Optional

from taggarr.config_schema import (
    Config, DefaultsConfig, InstanceConfig, TagsConfig
)


class ConfigError(Exception):
    """Configuration loading error."""
    pass


def load_config(cli_path: "Optional[str]" = None) -> Config:
    """Load configuration from YAML file.

    Search order:
    1. CLI-specified path
    2. ./taggarr.yaml
    3. ~/.config/taggarr/config.yaml
    4. /etc/taggarr/config.yaml
    """
    search_paths = [
        Path("./taggarr.yaml"),
        Path.home() / ".config" / "taggarr" / "config.yaml",
        Path("/etc/taggarr/config.yaml"),
    ]

    if cli_path:
        config_path = Path(cli_path)
        if not config_path.exists():
            raise ConfigError(f"Config file not found: {cli_path}")
    else:
        config_path = None
        for path in search_paths:
            if path.exists():
                config_path = path
                break

        if config_path is None:
            searched = "\n  ".join(str(p) for p in search_paths)
            raise ConfigError(
                f"No config file found. Searched:\n  {searched}\n\n"
                "Create taggarr.yaml or specify --config path"
            )

    return _parse_config(config_path)


def _parse_config(path: Path) -> Config:
    """Parse YAML config file."""
    try:
        with open(path) as f:
            raw = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigError(f"Invalid YAML in {path}: {e}")

    if not isinstance(raw, dict):
        raise ConfigError(f"Config must be a YAML mapping, got {type(raw).__name__}")

    # Parse defaults
    defaults_raw = raw.get("defaults", {})
    defaults = _parse_defaults(defaults_raw)

    # Parse instances
    instances_raw = raw.get("instances", {})
    if not instances_raw:
        raise ConfigError("No instances configured")

    instances = {}
    for name, inst_raw in instances_raw.items():
        instances[name] = _parse_instance(name, inst_raw, defaults)

    return Config(defaults=defaults, instances=instances)


def _parse_defaults(raw: dict) -> DefaultsConfig:
    """Parse defaults section."""
    tags_raw = raw.get("tags", {})
    tags = TagsConfig(
        dub=_interpolate(tags_raw.get("dub", "dub")),
        semi=_interpolate(tags_raw.get("semi", "semi-dub")),
        wrong=_interpolate(tags_raw.get("wrong", "wrong-dub")),
    )

    target_langs = raw.get("target_languages", ["en"])
    if isinstance(target_langs, str):
        target_langs = [lang.strip() for lang in target_langs.split(",")]

    return DefaultsConfig(
        target_languages=[_interpolate(lang) for lang in target_langs],
        tags=tags,
        dry_run=raw.get("dry_run", False),
        quick_mode=raw.get("quick_mode", False),
        run_interval_seconds=raw.get("run_interval_seconds", 7200),
        log_level=_interpolate(raw.get("log_level", "INFO")),
        log_path=_interpolate(raw.get("log_path", "/logs")),
    )


def _parse_instance(name: str, raw: dict, defaults: DefaultsConfig) -> InstanceConfig:
    """Parse a single instance, merging with defaults."""
    # Required fields
    for field in ["type", "url", "api_key", "root_path"]:
        if field not in raw:
            raise ConfigError(f"Instance '{name}' missing required field: {field}")

    inst_type = raw["type"]
    if inst_type not in ("sonarr", "radarr"):
        raise ConfigError(f"Instance '{name}' has invalid type: {inst_type}")

    # Tags: merge with defaults
    tags_raw = raw.get("tags", {})
    tags = TagsConfig(
        dub=_interpolate(tags_raw.get("dub", defaults.tags.dub)),
        semi=_interpolate(tags_raw.get("semi", defaults.tags.semi)),
        wrong=_interpolate(tags_raw.get("wrong", defaults.tags.wrong)),
    )

    # Target languages: use instance or default
    target_langs = raw.get("target_languages", defaults.target_languages)
    if isinstance(target_langs, str):
        target_langs = [lang.strip() for lang in target_langs.split(",")]

    return InstanceConfig(
        name=name,
        type=inst_type,
        url=_interpolate(raw["url"]).rstrip("/"),
        api_key=_interpolate(raw["api_key"]),
        root_path=_interpolate(raw["root_path"]),
        target_languages=[_interpolate(lang) for lang in target_langs],
        tags=tags,
        dry_run=raw.get("dry_run", defaults.dry_run),
        quick_mode=raw.get("quick_mode", defaults.quick_mode),
        target_genre=_interpolate(raw.get("target_genre")) if raw.get("target_genre") else None,
    )


def _interpolate(value: "Optional[str]") -> "Optional[str]":
    """Expand ${VAR} references in a string value."""
    if value is None:
        return None
    if not isinstance(value, str):
        return value

    pattern = re.compile(r'\$\{([^}]+)\}')

    def replacer(match):
        var_name = match.group(1)
        env_value = os.environ.get(var_name)
        if env_value is None:
            raise ConfigError(f"Environment variable not set: {var_name}")
        return env_value

    return pattern.sub(replacer, value)
