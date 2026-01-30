"""Taggarr - Dub Analysis & Tagging."""

__description__ = "Dub Analysis & Tagging."
__author__ = "BASSHOUS3"
__version__ = "0.5.0"

import time
import logging

from taggarr.config import (
    SONARR_ENABLED, RADARR_ENABLED,
    TAGGARR_JSON_PATH, TAGGARR_MOVIES_JSON_PATH,
    RUN_INTERVAL_SECONDS
)
from taggarr.logging_setup import setup_logging
from taggarr.storage import json_store
from taggarr.processors import tv, movies

_logger = None


def run(opts):
    """Run a single scan cycle."""
    global _logger
    if _logger is None:
        _logger = setup_logging()

    _logger.info(f"Taggarr - {__description__}")
    time.sleep(1)
    _logger.info(f"Taggarr - v{__version__} started.")
    time.sleep(1)
    _logger.info("Starting Taggarr scan...")
    time.sleep(5)

    # Log environment
    _logger.debug(f"SONARR_ENABLED={SONARR_ENABLED}, RADARR_ENABLED={RADARR_ENABLED}")
    time.sleep(3)

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

    # Process TV shows
    if SONARR_ENABLED:
        _logger.info("Sonarr enabled - processing TV shows...")
        taggarr_data = json_store.load(TAGGARR_JSON_PATH, key="series")
        taggarr_data = tv.process_all(opts, taggarr_data)
        json_store.save(TAGGARR_JSON_PATH, taggarr_data, key="series")
    else:
        _logger.info("Sonarr not configured - skipping TV shows")

    # Process movies
    if RADARR_ENABLED:
        _logger.info("Radarr enabled - processing movies...")
        taggarr_movies = json_store.load(TAGGARR_MOVIES_JSON_PATH, key="movies")
        taggarr_movies = movies.process_all(opts, taggarr_movies)
        json_store.save(TAGGARR_MOVIES_JSON_PATH, taggarr_movies, key="movies")
    else:
        _logger.info("Radarr not configured - skipping movies")

    _logger.info("Finished Taggarr scan.")
    _logger.info("Check out Huntarr.io to hunt missing dubs!")
    _logger.info(f"Next scan in {RUN_INTERVAL_SECONDS / 3600} hours.")


def run_loop(opts):
    """Run scans continuously at configured interval."""
    while True:
        run(opts)
        time.sleep(RUN_INTERVAL_SECONDS)
