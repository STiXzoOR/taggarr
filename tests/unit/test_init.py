"""Tests for taggarr package entry points."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from types import SimpleNamespace

import taggarr
from taggarr import run, run_loop, _process_instance
from taggarr.config_schema import Config, DefaultsConfig, InstanceConfig, TagsConfig


@pytest.fixture
def opts():
    """Default command line options."""
    return SimpleNamespace(
        quick=False,
        dry_run=False,
        write_mode=0,
        instances=None,
    )


@pytest.fixture
def config(tmp_path):
    """Test configuration."""
    return Config(
        defaults=DefaultsConfig(log_path=str(tmp_path)),
        instances={
            "sonarr": InstanceConfig(
                name="sonarr",
                type="sonarr",
                url="http://sonarr:8989",
                api_key="key",
                root_path=str(tmp_path / "tv"),
                target_languages=["en"],
                tags=TagsConfig(),
            ),
        },
    )


@pytest.fixture(autouse=True)
def reset_logger():
    """Reset the global logger before each test."""
    taggarr._logger = None
    yield
    taggarr._logger = None


class TestRun:
    """Tests for run function."""

    @patch("taggarr._process_instance")
    @patch("taggarr.setup_logging")
    def test_processes_all_instances(self, mock_logging, mock_process, opts, config, tmp_path):
        mock_logging.return_value = MagicMock()
        (tmp_path / "tv").mkdir()

        run(opts, config)

        mock_process.assert_called_once()

    @patch("taggarr._process_instance")
    @patch("taggarr.setup_logging")
    def test_filters_instances_when_specified(self, mock_logging, mock_process, opts, config, tmp_path):
        mock_logging.return_value = MagicMock()
        opts.instances = "nonexistent"

        run(opts, config)

        mock_process.assert_not_called()

    @patch("taggarr._process_instance")
    @patch("taggarr.setup_logging")
    def test_logs_quick_mode(self, mock_logging, mock_process, opts, config, tmp_path):
        mock_logger = MagicMock()
        mock_logging.return_value = mock_logger
        opts.quick = True
        (tmp_path / "tv").mkdir()

        run(opts, config)

        # Check quick mode was logged
        mock_logger.info.assert_any_call("Quick mode: Scanning only first episode per season.")

    @patch("taggarr._process_instance")
    @patch("taggarr.setup_logging")
    def test_logs_dry_run_mode(self, mock_logging, mock_process, opts, config, tmp_path):
        mock_logger = MagicMock()
        mock_logging.return_value = mock_logger
        opts.dry_run = True
        (tmp_path / "tv").mkdir()

        run(opts, config)

        mock_logger.info.assert_any_call("Dry run mode: No API calls or file edits.")

    @patch("taggarr._process_instance")
    @patch("taggarr.setup_logging")
    def test_logs_write_mode_0(self, mock_logging, mock_process, opts, config, tmp_path):
        mock_logger = MagicMock()
        mock_logging.return_value = mock_logger
        opts.write_mode = 0
        (tmp_path / "tv").mkdir()

        run(opts, config)

        mock_logger.info.assert_any_call("Write mode 0: Processing as usual.")

    @patch("taggarr._process_instance")
    @patch("taggarr.setup_logging")
    def test_logs_rewrite_mode(self, mock_logging, mock_process, opts, config, tmp_path):
        mock_logger = MagicMock()
        mock_logging.return_value = mock_logger
        opts.write_mode = 1
        (tmp_path / "tv").mkdir()

        run(opts, config)

        mock_logger.info.assert_any_call("Rewrite mode: Everything will be rebuilt.")

    @patch("taggarr._process_instance")
    @patch("taggarr.setup_logging")
    def test_logs_remove_mode(self, mock_logging, mock_process, opts, config, tmp_path):
        mock_logger = MagicMock()
        mock_logging.return_value = mock_logger
        opts.write_mode = 2
        (tmp_path / "tv").mkdir()

        run(opts, config)

        mock_logger.info.assert_any_call("Remove mode: Everything will be removed.")

    @patch("taggarr._process_instance")
    @patch("taggarr.setup_logging")
    def test_handles_unknown_write_mode(self, mock_logging, mock_process, opts, config, tmp_path):
        """Test that unknown write_mode values are silently handled."""
        mock_logger = MagicMock()
        mock_logging.return_value = mock_logger
        opts.write_mode = 99  # Unknown value
        (tmp_path / "tv").mkdir()

        run(opts, config)

        # Should not log any write mode message
        write_mode_calls = [
            call for call in mock_logger.info.call_args_list
            if "mode" in str(call).lower() and ("processing" in str(call).lower() or "rewrite" in str(call).lower() or "remove" in str(call).lower())
        ]
        assert len(write_mode_calls) == 0

    @patch("taggarr._process_instance")
    @patch("taggarr.setup_logging")
    def test_handles_instance_error(self, mock_logging, mock_process, opts, config, tmp_path):
        mock_logger = MagicMock()
        mock_logging.return_value = mock_logger
        mock_process.side_effect = Exception("Test error")
        (tmp_path / "tv").mkdir()

        # Should not raise
        run(opts, config)

        mock_logger.error.assert_called()

    @patch("taggarr._process_instance")
    @patch("taggarr.setup_logging")
    def test_filters_specific_instance(self, mock_logging, mock_process, opts, config, tmp_path):
        mock_logging.return_value = MagicMock()
        opts.instances = "sonarr"
        (tmp_path / "tv").mkdir()

        run(opts, config)

        mock_process.assert_called_once()


class TestProcessInstance:
    """Tests for _process_instance function."""

    @patch("taggarr.tv.process_all")
    @patch("taggarr.json_store.save")
    @patch("taggarr.json_store.load")
    @patch("taggarr.SonarrClient")
    def test_processes_sonarr_instance(self, mock_client, mock_load, mock_save, mock_process, opts, tmp_path):
        instance = InstanceConfig(
            name="sonarr",
            type="sonarr",
            url="http://sonarr:8989",
            api_key="key",
            root_path=str(tmp_path),
            target_languages=["en"],
            tags=TagsConfig(),
        )
        mock_load.return_value = {"series": {}}
        mock_process.return_value = {"series": {}}

        _process_instance(instance, opts)

        mock_client.assert_called_once_with("http://sonarr:8989", "key")
        mock_process.assert_called_once()
        mock_save.assert_called_once()

    @patch("taggarr.movies.process_all")
    @patch("taggarr.json_store.save")
    @patch("taggarr.json_store.load")
    @patch("taggarr.RadarrClient")
    def test_processes_radarr_instance(self, mock_client, mock_load, mock_save, mock_process, opts, tmp_path):
        instance = InstanceConfig(
            name="radarr",
            type="radarr",
            url="http://radarr:7878",
            api_key="key",
            root_path=str(tmp_path),
            target_languages=["en"],
            tags=TagsConfig(),
        )
        mock_load.return_value = {"movies": {}}
        mock_process.return_value = {"movies": {}}

        _process_instance(instance, opts)

        mock_client.assert_called_once_with("http://radarr:7878", "key")
        mock_process.assert_called_once()

    @patch("taggarr.tv.process_all")
    @patch("taggarr.json_store.save")
    @patch("taggarr.json_store.load")
    @patch("taggarr.SonarrClient")
    def test_loads_and_saves_correct_json_path(self, mock_client, mock_load, mock_save, mock_process, opts, tmp_path):
        instance = InstanceConfig(
            name="sonarr",
            type="sonarr",
            url="http://sonarr:8989",
            api_key="key",
            root_path=str(tmp_path),
            target_languages=["en"],
            tags=TagsConfig(),
        )
        mock_load.return_value = {"series": {}}
        mock_process.return_value = {"series": {"show": {}}}

        _process_instance(instance, opts)

        expected_path = str(tmp_path / "taggarr.json")
        mock_load.assert_called_once_with(expected_path, key="series")
        mock_save.assert_called_once()


class TestRunLoop:
    """Tests for run_loop function."""

    @patch("taggarr.run")
    def test_calls_run_then_stops(self, mock_run, opts, config):
        import threading
        stop = threading.Event()
        # Signal stop after first run completes
        mock_run.side_effect = lambda *args: stop.set()

        run_loop(opts, config, stop_event=stop)

        mock_run.assert_called_once()

    @patch("taggarr.run")
    def test_respects_stop_event(self, mock_run, opts, config):
        import threading
        stop = threading.Event()
        stop.set()  # Already stopped

        run_loop(opts, config, stop_event=stop)

        mock_run.assert_not_called()

    @patch("taggarr.run")
    def test_runs_multiple_cycles_before_stop(self, mock_run, opts, config):
        import threading
        config.defaults.run_interval_seconds = 0
        stop = threading.Event()
        call_count = [0]

        def track_and_stop(*args):
            call_count[0] += 1
            if call_count[0] >= 2:
                stop.set()

        mock_run.side_effect = track_and_stop

        run_loop(opts, config, stop_event=stop)

        assert mock_run.call_count == 2


class TestRunLoopSignalHandler:
    """Tests for run_loop signal handler setup when no stop_event provided."""

    @patch("taggarr.run")
    @patch("taggarr.signal.signal")
    def test_registers_signal_handlers_when_no_stop_event(
        self, mock_signal, mock_run, opts, config
    ):
        """run_loop registers SIGINT/SIGTERM handlers when stop_event is None."""
        import signal as sig
        import taggarr

        taggarr._logger = MagicMock()

        # Make run() set the internally-created stop event via the signal handler
        def stop_via_handler(*args):
            # Find the registered handler and call it
            for call in mock_signal.call_args_list:
                if call[0][0] == sig.SIGINT:
                    handler = call[0][1]
                    handler(sig.SIGINT, None)
                    return

        mock_run.side_effect = stop_via_handler

        run_loop(opts, config, stop_event=None)

        # Verify signal handlers were registered
        signal_calls = [call[0][0] for call in mock_signal.call_args_list]
        assert sig.SIGINT in signal_calls
        assert sig.SIGTERM in signal_calls

    @patch("taggarr.run")
    @patch("taggarr.signal.signal")
    def test_signal_handler_sets_stop_event(self, mock_signal, mock_run, opts, config):
        """Signal handler sets the internal stop event."""
        import signal as sig
        import taggarr

        taggarr._logger = MagicMock()

        captured_handler = [None]

        def capture_handler(signum, handler):
            if signum == sig.SIGINT:
                captured_handler[0] = handler

        mock_signal.side_effect = capture_handler

        # After first run, invoke the captured handler
        def trigger_stop(*args):
            if captured_handler[0]:
                captured_handler[0](sig.SIGINT, None)

        mock_run.side_effect = trigger_stop

        run_loop(opts, config, stop_event=None)

        mock_run.assert_called_once()
        taggarr._logger.info.assert_any_call("Taggarr stopped.")


class TestProcessInstanceEdgeCases:
    """Edge case tests for _process_instance function."""

    def test_unknown_instance_type_does_nothing(self, opts, tmp_path):
        """Test that unknown instance type simply returns without error."""
        instance = InstanceConfig(
            name="unknown",
            type="unknown",
            url="http://unknown:8000",
            api_key="key",
            root_path=str(tmp_path),
            target_languages=["en"],
            tags=TagsConfig(),
        )

        # Should not raise - just returns without doing anything
        _process_instance(instance, opts)

    @patch("taggarr._process_instance")
    @patch("taggarr.setup_logging")
    def test_uses_existing_logger(self, mock_logging, mock_process, opts, config, tmp_path):
        """Test that existing logger is reused."""
        import taggarr
        mock_logger = MagicMock()
        taggarr._logger = mock_logger  # Pre-set logger
        (tmp_path / "tv").mkdir()

        run(opts, config)

        # setup_logging should NOT be called since _logger is already set
        mock_logging.assert_not_called()
        # But the logger should be used
        mock_logger.info.assert_called()
