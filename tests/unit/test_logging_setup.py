"""Tests for taggarr.logging_setup module."""

import logging
import pytest

from taggarr.logging_setup import setup_logging


class TestSetupLogging:
    """Tests for setup_logging function."""

    def test_creates_logger_with_name(self, tmp_path):
        logger = setup_logging(path=str(tmp_path))

        assert logger.name == "taggarr"

    def test_sets_log_level_from_string(self, tmp_path):
        # Clear any existing handlers first
        existing_logger = logging.getLogger("taggarr")
        existing_logger.handlers.clear()

        logger = setup_logging(level="DEBUG", path=str(tmp_path))

        assert logger.level == logging.DEBUG

    def test_defaults_to_info_for_invalid_level(self, tmp_path):
        # Clear any existing handlers first
        existing_logger = logging.getLogger("taggarr")
        existing_logger.handlers.clear()

        logger = setup_logging(level="INVALID", path=str(tmp_path))

        assert logger.level == logging.INFO

    def test_creates_log_directory(self, tmp_path):
        log_path = tmp_path / "nested" / "logs"

        setup_logging(path=str(log_path))

        assert log_path.exists()

    def test_creates_log_file(self, tmp_path):
        # Clear any existing handlers first
        existing_logger = logging.getLogger("taggarr")
        existing_logger.handlers.clear()

        setup_logging(path=str(tmp_path))

        log_files = list(tmp_path.glob("taggarr*.log"))
        assert len(log_files) >= 1

    def test_adds_file_and_stream_handlers(self, tmp_path):
        # Clear any existing handlers
        logger = logging.getLogger("taggarr")
        logger.handlers.clear()

        logger = setup_logging(path=str(tmp_path))

        handler_types = [type(h).__name__ for h in logger.handlers]
        assert "FileHandler" in handler_types
        assert "StreamHandler" in handler_types

    def test_sets_warning_level(self, tmp_path):
        # Clear any existing handlers first
        existing_logger = logging.getLogger("taggarr")
        existing_logger.handlers.clear()

        logger = setup_logging(level="WARNING", path=str(tmp_path))

        assert logger.level == logging.WARNING

    def test_sets_error_level(self, tmp_path):
        # Clear any existing handlers first
        existing_logger = logging.getLogger("taggarr")
        existing_logger.handlers.clear()

        logger = setup_logging(level="ERROR", path=str(tmp_path))

        assert logger.level == logging.ERROR

    def test_log_file_contains_version(self, tmp_path):
        # Clear any existing handlers first
        existing_logger = logging.getLogger("taggarr")
        existing_logger.handlers.clear()

        setup_logging(path=str(tmp_path))

        log_files = list(tmp_path.glob("taggarr*.log"))
        assert len(log_files) >= 1
        # File name should contain version in parentheses
        assert any("taggarr(" in f.name for f in log_files)
