"""Taggarr - Dub Analysis & Tagging.

Fork of https://github.com/BassHous3/taggarr
"""

__description__ = "Dub Analysis & Tagging."
__author__ = "STiXzoOR (fork), BassHous3 (original)"
__version__ = "0.8.0"

import os
import time
import logging

from taggarr.config_loader import load_config, ConfigError
from taggarr.config_schema import Config, InstanceConfig
from taggarr.logging_setup import setup_logging
from taggarr.storage import json_store
from taggarr.processors import tv, movies
from taggarr.services.sonarr import SonarrClient
from taggarr.services.radarr import RadarrClient

_logger = None


def run(opts, config: Config):
    """Run a single scan cycle for all configured instances."""
    global _logger
    if _logger is None:
        _logger = setup_logging(
            level=config.defaults.log_level,
            path=config.defaults.log_path
        )

    _logger.info(f"Taggarr - {__description__}")
    _logger.info(f"Taggarr - v{__version__} started.")
    _logger.info("Starting Taggarr scan...")

    # Filter instances if specified
    instance_filter = getattr(opts, 'instances', None)
    if instance_filter:
        instance_names = [n.strip() for n in instance_filter.split(",")]
        instances = {k: v for k, v in config.instances.items() if k in instance_names}
        if not instances:
            _logger.error(f"No matching instances found for: {instance_filter}")
            return
    else:
        instances = config.instances

    # Log mode info
    if opts.quick:
        _logger.info("Quick mode: Scanning only first episode per season.")
    if opts.dry_run:
        _logger.info("Dry run mode: No API calls or file edits.")
    if opts.write_mode == 0:
        _logger.info("Write mode 0: Processing as usual.")
    elif opts.write_mode == 1:
        _logger.info("Rewrite mode: Everything will be rebuilt.")
    elif opts.write_mode == 2:
        _logger.info("Remove mode: Everything will be removed.")

    # Process each instance
    for name, instance in instances.items():
        _logger.info(f"Processing instance: {name} ({instance.type} @ {instance.url})")

        try:
            _process_instance(instance, opts)
        except Exception as e:
            _logger.error(f"Failed to process instance {name}: {e}")
            continue

    _logger.info("Finished Taggarr scan.")
    _logger.info(f"Next scan in {config.defaults.run_interval_seconds / 3600} hours.")


def _process_instance(instance: InstanceConfig, opts) -> None:
    """Process a single Sonarr/Radarr instance."""
    global _logger

    json_path = os.path.join(instance.root_path, "taggarr.json")

    if instance.type == "sonarr":
        client = SonarrClient(instance.url, instance.api_key)
        taggarr_data = json_store.load(json_path, key="series")
        taggarr_data = tv.process_all(client, instance, opts, taggarr_data)
        json_store.save(json_path, taggarr_data, key="series")

    elif instance.type == "radarr":
        client = RadarrClient(instance.url, instance.api_key)
        taggarr_data = json_store.load(json_path, key="movies")
        taggarr_data = movies.process_all(client, instance, opts, taggarr_data)
        json_store.save(json_path, taggarr_data, key="movies")


def run_loop(opts, config: Config):
    """Run scans continuously at configured interval."""
    while True:
        run(opts, config)
        time.sleep(config.defaults.run_interval_seconds)
