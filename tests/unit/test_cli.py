"""Tests for taggarr CLI (main.py)."""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


class TestServeCommand:
    """Tests for the serve command."""

    def test_serve_command_exists(self) -> None:
        """The serve subcommand is registered."""
        from main import main

        # Test that --help for serve doesn't error
        with patch.object(sys, "argv", ["taggarr", "serve", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            # argparse exits with 0 for --help
            assert exc_info.value.code == 0

    def test_serve_command_calls_run_server(self, tmp_path: Path) -> None:
        """serve command invokes run_server with correct arguments."""
        db_path = tmp_path / "test.db"

        with patch("taggarr.server.run_server") as mock_run_server:
            with patch.object(sys, "argv", [
                "taggarr", "serve",
                "--host", "127.0.0.1",
                "--port", "9000",
                "--base-url", "/api",
                "--db", str(db_path),
                "--reload",
            ]):
                from main import main
                main()

            mock_run_server.assert_called_once_with(
                host="127.0.0.1",
                port=9000,
                base_url="/api",
                db_path=db_path,
                reload=True,
            )

    def test_serve_command_uses_defaults(self) -> None:
        """serve command uses default values when options not specified."""
        with patch("taggarr.server.run_server") as mock_run_server:
            with patch.object(sys, "argv", ["taggarr", "serve"]):
                from main import main
                main()

            mock_run_server.assert_called_once_with(
                host="0.0.0.0",
                port=8080,
                base_url="/",
                db_path=None,
                reload=False,
            )


class TestScanCommand:
    """Tests for the scan command (backwards compatibility)."""

    def test_scan_command_exists(self) -> None:
        """The scan subcommand is registered."""
        with patch.object(sys, "argv", ["taggarr", "scan", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                from main import main
                main()
            assert exc_info.value.code == 0

    def test_default_behavior_runs_scan(self, mocker) -> None:
        """Running without subcommand defaults to scan behavior."""
        mock_load_config = mocker.patch("main.load_config")
        mock_run = mocker.patch("taggarr.run")
        mock_config = MagicMock()
        mock_load_config.return_value = mock_config

        with patch.object(sys, "argv", ["taggarr"]):
            from main import main
            main()

        mock_run.assert_called_once()

    def test_scan_command_with_loop_flag(self, mocker) -> None:
        """scan command with --loop runs continuously."""
        mock_load_config = mocker.patch("main.load_config")
        mock_run_loop = mocker.patch("taggarr.run_loop")
        mock_config = MagicMock()
        mock_load_config.return_value = mock_config

        with patch.object(sys, "argv", ["taggarr", "scan", "--loop"]):
            from main import main
            main()

        mock_run_loop.assert_called_once()

    def test_legacy_args_without_subcommand(self, mocker) -> None:
        """Legacy arguments work without explicit 'scan' subcommand."""
        mock_load_config = mocker.patch("main.load_config")
        mock_run = mocker.patch("taggarr.run")
        mock_config = MagicMock()
        mock_load_config.return_value = mock_config

        with patch.object(sys, "argv", ["taggarr", "--quick", "--dry-run"]):
            from main import main
            main()

        mock_run.assert_called_once()
        # Verify the opts have the flags set
        call_args = mock_run.call_args[0]
        opts = call_args[0]
        assert opts.quick is True
        assert opts.dry_run is True
