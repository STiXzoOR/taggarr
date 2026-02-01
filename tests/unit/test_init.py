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

    @patch("taggarr.time.sleep")
    @patch("taggarr.run")
    def test_calls_run_repeatedly(self, mock_run, mock_sleep, opts, config):
        # Make sleep raise to break the loop
        mock_sleep.side_effect = [None, KeyboardInterrupt]

        with pytest.raises(KeyboardInterrupt):
            run_loop(opts, config)

        assert mock_run.call_count == 2
        mock_sleep.assert_called_with(config.defaults.run_interval_seconds)

    @patch("taggarr.time.sleep")
    @patch("taggarr.run")
    def test_sleeps_for_configured_interval(self, mock_run, mock_sleep, opts, config):
        config.defaults.run_interval_seconds = 3600  # 1 hour
        mock_sleep.side_effect = KeyboardInterrupt

        with pytest.raises(KeyboardInterrupt):
            run_loop(opts, config)

        mock_sleep.assert_called_with(3600)
