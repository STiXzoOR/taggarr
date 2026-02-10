"""Tests for taggarr.processors.tv module."""

import logging
import os
import pytest
from unittest.mock import Mock, patch, MagicMock
from types import SimpleNamespace

from taggarr.processors import tv
from taggarr.config_schema import InstanceConfig, TagsConfig


@pytest.fixture
def opts():
    """Default command line options."""
    return SimpleNamespace(quick=False, dry_run=False, write_mode=0)


@pytest.fixture
def instance():
    """Sonarr instance config."""
    return InstanceConfig(
        name="test",
        type="sonarr",
        url="http://sonarr:8989",
        api_key="key",
        root_path="/media/tv",
        target_languages=["en"],
        tags=TagsConfig(),
        dry_run=False,
        quick_mode=False,
        target_genre=None,
    )


class TestDetermineStatus:
    """Tests for _determine_status function."""

    def test_returns_wrong_dub_when_unexpected_languages(self):
        stats = {"unexpected_languages": ["de"], "dub": ["E01"], "missing_dub": []}

        result = tv._determine_status(stats)

        assert result == "wrong-dub"

    def test_returns_fully_dub_when_all_episodes_dubbed(self):
        stats = {"unexpected_languages": [], "dub": ["E01", "E02"], "missing_dub": []}

        result = tv._determine_status(stats)

        assert result == "fully-dub"

    def test_returns_semi_dub_when_some_missing(self):
        stats = {"unexpected_languages": [], "dub": ["E01"], "missing_dub": ["E02"]}

        result = tv._determine_status(stats)

        assert result == "semi-dub"

    def test_returns_original_when_no_dub(self):
        stats = {"unexpected_languages": [], "dub": [], "missing_dub": []}

        result = tv._determine_status(stats)

        assert result == "original"


class TestPassesGenreFilter:
    """Tests for _passes_genre_filter function."""

    def test_returns_true_when_no_filter(self, tmp_path):
        nfo_path = tmp_path / "tvshow.nfo"
        nfo_path.write_text("<tvshow><genre>Action</genre></tvshow>")

        result = tv._passes_genre_filter(str(nfo_path), None)

        assert result is True

    def test_returns_true_when_genre_matches(self, tmp_path):
        nfo_path = tmp_path / "tvshow.nfo"
        nfo_path.write_text("<tvshow><genre>Anime</genre></tvshow>")

        result = tv._passes_genre_filter(str(nfo_path), "anime")

        assert result is True

    def test_returns_false_when_genre_not_found(self, tmp_path):
        nfo_path = tmp_path / "tvshow.nfo"
        nfo_path.write_text("<tvshow><genre>Drama</genre></tvshow>")

        result = tv._passes_genre_filter(str(nfo_path), "anime")

        assert result is False


class TestHasChanges:
    """Tests for _has_changes function."""

    def test_returns_true_when_season_modified(self, tmp_path):
        show_path = tmp_path / "Show"
        season_path = show_path / "Season 01"
        season_path.mkdir(parents=True)

        saved_seasons = {"Season 01": {"last_modified": 0}}

        result = tv._has_changes(str(show_path), saved_seasons)

        assert result is True

    def test_returns_false_when_no_changes(self, tmp_path):
        show_path = tmp_path / "Show"
        season_path = show_path / "Season 01"
        season_path.mkdir(parents=True)

        current_mtime = os.path.getmtime(str(season_path))
        saved_seasons = {"Season 01": {"last_modified": current_mtime + 1}}

        result = tv._has_changes(str(show_path), saved_seasons)

        assert result is False

    def test_ignores_non_season_directories(self, tmp_path):
        show_path = tmp_path / "Show"
        (show_path / "Season 01").mkdir(parents=True)
        (show_path / "Extras").mkdir()

        current_mtime = os.path.getmtime(str(show_path / "Season 01"))
        saved_seasons = {"Season 01": {"last_modified": current_mtime + 1}}

        result = tv._has_changes(str(show_path), saved_seasons)

        assert result is False


class TestHasNewSeasons:
    """Tests for _has_new_seasons function."""

    def test_returns_true_when_new_season_exists(self, tmp_path):
        show_path = tmp_path / "Show"
        (show_path / "Season 01").mkdir(parents=True)
        (show_path / "Season 02").mkdir(parents=True)

        saved_seasons = {"Season 01": {}}

        result = tv._has_new_seasons(str(show_path), saved_seasons)

        assert result is True

    def test_returns_false_when_no_new_seasons(self, tmp_path):
        show_path = tmp_path / "Show"
        (show_path / "Season 01").mkdir(parents=True)

        saved_seasons = {"Season 01": {}}

        result = tv._has_new_seasons(str(show_path), saved_seasons)

        assert result is False

    def test_ignores_non_season_directories(self, tmp_path):
        show_path = tmp_path / "Show"
        (show_path / "Season 01").mkdir(parents=True)
        (show_path / "Extras").mkdir()

        saved_seasons = {"Season 01": {}}

        result = tv._has_new_seasons(str(show_path), saved_seasons)

        assert result is False


class TestApplyTags:
    """Tests for _apply_tags function."""

    def test_adds_dub_tag_and_removes_others(self, instance):
        client = Mock()

        tv._apply_tags(client, 1, instance.tags.dub, instance, False)

        client.apply_tag_changes.assert_called_once_with(
            1, add_tags=["dub"], remove_tags=["semi-dub", "wrong-dub"], dry_run=False
        )

    def test_adds_semi_tag_and_removes_others(self, instance):
        client = Mock()

        tv._apply_tags(client, 1, instance.tags.semi, instance, False)

        client.apply_tag_changes.assert_called_once_with(
            1, add_tags=["semi-dub"], remove_tags=["dub", "wrong-dub"], dry_run=False
        )

    def test_adds_wrong_tag_and_removes_others(self, instance):
        client = Mock()

        tv._apply_tags(client, 1, instance.tags.wrong, instance, False)

        client.apply_tag_changes.assert_called_once_with(
            1, add_tags=["wrong-dub"], remove_tags=["dub", "semi-dub"], dry_run=False
        )

    def test_removes_all_tags_when_no_tag(self, instance, caplog):
        caplog.set_level(logging.INFO)
        client = Mock()

        tv._apply_tags(client, 1, None, instance, False)

        client.apply_tag_changes.assert_called_once_with(
            1, add_tags=[], remove_tags=["dub", "semi-dub", "wrong-dub"], dry_run=False
        )
        assert "Removing all tags" in caplog.text


class TestBuildEntry:
    """Tests for _build_entry function."""

    def test_builds_entry_with_all_fields(self):
        series = {"originalLanguage": {"name": "Japanese"}}
        seasons = {"Season 01": {"status": "fully-dub"}}

        result = tv._build_entry("Test Show", "dub", seasons, series, 12345.0)

        assert result["display_name"] == "Test Show"
        assert result["tag"] == "dub"
        assert result["original_language"] == "japanese"
        assert result["seasons"] == seasons
        assert result["last_modified"] == 12345.0
        assert "last_scan" in result

    def test_handles_string_original_language(self):
        series = {"originalLanguage": "English"}

        result = tv._build_entry("Test", "dub", {}, series, 0)

        assert result["original_language"] == "english"

    def test_uses_none_string_when_no_tag(self):
        series = {"originalLanguage": "English"}

        result = tv._build_entry("Test", None, {}, series, 0)

        assert result["tag"] == "none"

    def test_handles_missing_original_language(self):
        series = {}

        result = tv._build_entry("Test", "dub", {}, series, 0)

        assert result["original_language"] == ""


class TestScanSeason:
    """Tests for _scan_season function."""

    @patch("taggarr.processors.tv.media.analyze_audio")
    def test_scans_video_files(self, mock_analyze, tmp_path, instance):
        season_path = tmp_path / "Season 01"
        season_path.mkdir()
        (season_path / "S01E01.mkv").write_bytes(b"x")
        (season_path / "S01E02.mkv").write_bytes(b"x")

        mock_analyze.return_value = ["en"]
        series_meta = {"originalLanguage": {"name": "Japanese"}}

        stats = tv._scan_season(str(season_path), series_meta, instance, {"en", "eng"})

        assert stats["episodes"] == 2
        assert mock_analyze.call_count == 2

    @patch("taggarr.processors.tv.media.analyze_audio")
    def test_quick_mode_scans_only_first(self, mock_analyze, tmp_path, instance):
        season_path = tmp_path / "Season 01"
        season_path.mkdir()
        (season_path / "S01E01.mkv").write_bytes(b"x")
        (season_path / "S01E02.mkv").write_bytes(b"x")

        mock_analyze.return_value = ["en"]
        series_meta = {"originalLanguage": "Japanese"}

        stats = tv._scan_season(str(season_path), series_meta, instance, {"en"}, quick=True)

        assert stats["episodes"] == 1
        assert mock_analyze.call_count == 1

    @patch("taggarr.processors.tv.media.analyze_audio")
    def test_detects_fallback_original(self, mock_analyze, tmp_path, instance, caplog):
        caplog.set_level(logging.INFO)
        season_path = tmp_path / "Season 01"
        season_path.mkdir()
        (season_path / "S01E01.mkv").write_bytes(b"x")

        mock_analyze.return_value = ["__fallback_original__"]
        series_meta = {"originalLanguage": "Japanese"}

        stats = tv._scan_season(str(season_path), series_meta, instance, {"en"})

        assert "E01" in stats["original_dub"]
        assert "assuming original" in caplog.text

    @patch("taggarr.processors.tv.media.analyze_audio")
    def test_detects_target_language(self, mock_analyze, tmp_path, instance):
        season_path = tmp_path / "Season 01"
        season_path.mkdir()
        (season_path / "S01E01.mkv").write_bytes(b"x")

        mock_analyze.return_value = ["en", "ja"]
        series_meta = {"originalLanguage": {"name": "Japanese"}}

        stats = tv._scan_season(str(season_path), series_meta, instance, {"en", "eng"})

        assert len(stats["dub"]) == 1
        assert "E01" in stats["dub"][0]

    @patch("taggarr.processors.tv.media.analyze_audio")
    def test_detects_unexpected_language(self, mock_analyze, tmp_path, instance):
        season_path = tmp_path / "Season 01"
        season_path.mkdir()
        (season_path / "S01E01.mkv").write_bytes(b"x")

        mock_analyze.return_value = ["en", "de"]  # German is unexpected
        series_meta = {"originalLanguage": {"name": "Japanese"}}

        stats = tv._scan_season(str(season_path), series_meta, instance, {"en", "eng"})

        assert "de" in stats["unexpected_languages"]

    @patch("taggarr.processors.tv.media.analyze_audio")
    def test_handles_missing_target_language(self, mock_analyze, tmp_path, instance):
        season_path = tmp_path / "Season 01"
        season_path.mkdir()
        (season_path / "S01E01.mkv").write_bytes(b"x")

        mock_analyze.return_value = ["ja"]  # Only Japanese, missing English
        series_meta = {"originalLanguage": {"name": "Japanese"}}

        stats = tv._scan_season(str(season_path), series_meta, instance, {"en", "eng"})

        assert len(stats["missing_dub"]) == 1

    @patch("taggarr.processors.tv.media.analyze_audio")
    def test_handles_non_standard_filename(self, mock_analyze, tmp_path, instance):
        season_path = tmp_path / "Season 01"
        season_path.mkdir()
        (season_path / "episode_without_number.mkv").write_bytes(b"x")

        mock_analyze.return_value = ["en"]
        series_meta = {"originalLanguage": "Japanese"}

        stats = tv._scan_season(str(season_path), series_meta, instance, {"en"})

        # Should use filename without extension as episode name
        assert stats["episodes"] == 1


class TestScanShow:
    """Tests for _scan_show function."""

    @patch("taggarr.processors.tv._scan_season")
    def test_ignores_non_season_directories(self, mock_scan, tmp_path, instance):
        """Test that non-season directories are skipped."""
        show_path = tmp_path / "Show"
        (show_path / "Season 01").mkdir(parents=True)
        (show_path / "Extras").mkdir()  # Non-season dir
        (show_path / "file.txt").write_text("not a dir")  # File, not dir

        mock_scan.return_value = {
            "unexpected_languages": [],
            "dub": ["E01"],
            "missing_dub": [],
        }
        series_meta = {"originalLanguage": "Japanese"}

        tag, seasons = tv._scan_show(str(show_path), series_meta, instance, {"en"})

        # Only Season 01 should be scanned
        mock_scan.assert_called_once()
        assert "Season 01" in seasons
        assert "Extras" not in seasons

    @patch("taggarr.processors.tv._scan_season")
    def test_returns_wrong_when_unexpected_found(self, mock_scan, tmp_path, instance):
        show_path = tmp_path / "Show"
        (show_path / "Season 01").mkdir(parents=True)

        mock_scan.return_value = {
            "unexpected_languages": ["de"],
            "dub": ["E01"],
            "missing_dub": [],
        }
        series_meta = {"originalLanguage": "Japanese"}

        tag, seasons = tv._scan_show(str(show_path), series_meta, instance, {"en"})

        assert tag == instance.tags.wrong

    @patch("taggarr.processors.tv._scan_season")
    def test_returns_dub_when_all_fully_dubbed(self, mock_scan, tmp_path, instance):
        show_path = tmp_path / "Show"
        (show_path / "Season 01").mkdir(parents=True)

        mock_scan.return_value = {
            "unexpected_languages": [],
            "dub": ["E01", "E02"],
            "missing_dub": [],
        }
        series_meta = {"originalLanguage": "Japanese"}

        tag, seasons = tv._scan_show(str(show_path), series_meta, instance, {"en"})

        assert tag == instance.tags.dub

    @patch("taggarr.processors.tv._scan_season")
    def test_returns_semi_when_partially_dubbed(self, mock_scan, tmp_path, instance):
        show_path = tmp_path / "Show"
        (show_path / "Season 01").mkdir(parents=True)

        mock_scan.return_value = {
            "unexpected_languages": [],
            "dub": ["E01"],
            "missing_dub": ["E02"],
        }
        series_meta = {"originalLanguage": "Japanese"}

        tag, seasons = tv._scan_show(str(show_path), series_meta, instance, {"en"})

        assert tag == instance.tags.semi

    @patch("taggarr.processors.tv._scan_season")
    def test_returns_none_when_original_only(self, mock_scan, tmp_path, instance):
        show_path = tmp_path / "Show"
        (show_path / "Season 01").mkdir(parents=True)

        mock_scan.return_value = {
            "unexpected_languages": [],
            "dub": [],
            "missing_dub": [],
        }
        series_meta = {"originalLanguage": "Japanese"}

        tag, seasons = tv._scan_show(str(show_path), series_meta, instance, {"en"})

        assert tag is None


class TestProcessAll:
    """Tests for process_all function."""

    @patch("taggarr.processors.tv._scan_show")
    @patch("taggarr.processors.tv.nfo.update_tag")
    def test_skips_non_directory(self, mock_update_tag, mock_scan, tmp_path, opts, instance):
        """Test that non-directory entries are skipped."""
        instance.root_path = str(tmp_path)
        # Create a file instead of directory
        (tmp_path / "show.txt").write_text("not a directory")
        client = Mock()
        taggarr_data = {"series": {}}

        result = tv.process_all(client, instance, opts, taggarr_data)

        mock_scan.assert_not_called()
        assert result == {"series": {}}

    @patch("taggarr.processors.tv._scan_show")
    def test_skips_unchanged_show(self, mock_scan, tmp_path, opts, instance, caplog):
        """Test skipping shows with no changes (write_mode=0)."""
        caplog.set_level(logging.INFO)
        show_path = tmp_path / "TestShow"
        season_path = show_path / "Season 01"
        season_path.mkdir(parents=True)
        (show_path / "tvshow.nfo").write_text("<tvshow><genre>Drama</genre></tvshow>")

        instance.root_path = str(tmp_path)
        opts.write_mode = 0
        client = Mock()

        # Mark it as already processed with current mtime
        current_mtime = os.path.getmtime(str(season_path))
        taggarr_data = {
            "series": {
                str(show_path): {
                    "seasons": {"Season 01": {"last_modified": current_mtime + 1}}
                }
            }
        }

        tv.process_all(client, instance, opts, taggarr_data)

        mock_scan.assert_not_called()
        assert "no new or updated" in caplog.text

    @patch("taggarr.processors.tv._scan_show")
    def test_skips_show_without_nfo(self, mock_scan, tmp_path, opts, instance, caplog):
        """Test skipping shows without NFO file."""
        caplog.set_level(logging.DEBUG, logger="taggarr")
        show_path = tmp_path / "TestShow"
        (show_path / "Season 01").mkdir(parents=True)
        # No tvshow.nfo

        instance.root_path = str(tmp_path)
        client = Mock()
        taggarr_data = {"series": {}}

        tv.process_all(client, instance, opts, taggarr_data)

        mock_scan.assert_not_called()
        assert "No NFO found" in caplog.text

    @patch("taggarr.processors.tv._scan_show")
    def test_skips_genre_mismatch(self, mock_scan, tmp_path, opts, instance, caplog):
        """Test skipping shows that don't match genre filter."""
        caplog.set_level(logging.INFO)
        show_path = tmp_path / "TestShow"
        (show_path / "Season 01").mkdir(parents=True)
        (show_path / "tvshow.nfo").write_text("<tvshow><genre>Drama</genre></tvshow>")

        instance.root_path = str(tmp_path)
        instance.target_genre = "anime"
        client = Mock()
        taggarr_data = {"series": {}}

        tv.process_all(client, instance, opts, taggarr_data)

        mock_scan.assert_not_called()
        assert "genre mismatch" in caplog.text

    @patch("taggarr.processors.tv._scan_show")
    def test_skips_show_not_in_sonarr(self, mock_scan, tmp_path, opts, instance, caplog):
        """Test skipping shows not found in Sonarr."""
        caplog.set_level(logging.WARNING)
        show_path = tmp_path / "TestShow"
        (show_path / "Season 01").mkdir(parents=True)
        (show_path / "tvshow.nfo").write_text("<tvshow><genre>Drama</genre></tvshow>")

        instance.root_path = str(tmp_path)
        client = Mock()
        client.get_series_by_path.return_value = None
        taggarr_data = {"series": {}}

        tv.process_all(client, instance, opts, taggarr_data)

        mock_scan.assert_not_called()
        assert "No Sonarr metadata" in caplog.text

    @patch("taggarr.processors.tv._scan_show")
    @patch("taggarr.processors.tv.nfo.update_tag")
    def test_remove_mode_removes_tags(self, mock_update_tag, mock_scan, tmp_path, opts, instance, caplog):
        """Test remove mode (write_mode=2) removes all tags."""
        caplog.set_level(logging.INFO)
        show_path = tmp_path / "TestShow"
        (show_path / "Season 01").mkdir(parents=True)
        (show_path / "tvshow.nfo").write_text("<tvshow><genre>Drama</genre></tvshow>")

        instance.root_path = str(tmp_path)
        opts.write_mode = 2
        client = Mock()
        client.get_series_by_path.return_value = {"id": 123}
        taggarr_data = {"series": {str(show_path): {"seasons": {}}}}

        result = tv.process_all(client, instance, opts, taggarr_data)

        # Should call apply_tag_changes to remove all tags
        client.apply_tag_changes.assert_called_once_with(
            123, remove_tags=["dub", "semi-dub", "wrong-dub"], dry_run=False
        )
        # Show should be removed from data
        assert str(show_path) not in result["series"]
        assert "Removing tags" in caplog.text

    @patch("taggarr.processors.tv._scan_show")
    @patch("taggarr.processors.tv.nfo.update_tag")
    def test_remove_mode_handles_missing_show_in_data(self, mock_update_tag, mock_scan, tmp_path, opts, instance):
        """Test remove mode when show is not already in taggarr_data."""
        show_path = tmp_path / "TestShow"
        (show_path / "Season 01").mkdir(parents=True)
        (show_path / "tvshow.nfo").write_text("<tvshow><genre>Drama</genre></tvshow>")

        instance.root_path = str(tmp_path)
        opts.write_mode = 2
        client = Mock()
        client.get_series_by_path.return_value = {"id": 123}
        taggarr_data = {"series": {}}  # Show not in data

        result = tv.process_all(client, instance, opts, taggarr_data)

        # Should call apply_tag_changes to remove all tags
        client.apply_tag_changes.assert_called_once_with(
            123, remove_tags=["dub", "semi-dub", "wrong-dub"], dry_run=False
        )
        # Should not fail even though show wasn't in data
        assert str(show_path) not in result["series"]

    @patch("taggarr.processors.tv._scan_show")
    @patch("taggarr.processors.tv.nfo.update_tag")
    @patch("taggarr.processors.tv._apply_tags")
    def test_processes_new_show(self, mock_apply, mock_update_tag, mock_scan, tmp_path, opts, instance, caplog):
        """Test processing a new show."""
        caplog.set_level(logging.INFO)
        show_path = tmp_path / "TestShow"
        season_path = show_path / "Season 01"
        season_path.mkdir(parents=True)
        (show_path / "tvshow.nfo").write_text("<tvshow><genre>Drama</genre></tvshow>")

        instance.root_path = str(tmp_path)
        client = Mock()
        client.get_series_by_path.return_value = {"id": 123, "originalLanguage": "Japanese"}
        mock_scan.return_value = (instance.tags.dub, {"Season 01": {"status": "fully-dub"}})
        taggarr_data = {"series": {}}

        result = tv.process_all(client, instance, opts, taggarr_data)

        mock_scan.assert_called_once()
        mock_apply.assert_called_once()
        mock_update_tag.assert_called_once()
        assert str(show_path) in result["series"]
        assert "Processing show" in caplog.text

    @patch("taggarr.processors.tv._scan_show")
    @patch("taggarr.processors.tv.nfo.update_tag")
    @patch("taggarr.processors.tv._apply_tags")
    def test_rewrite_mode_refreshes_series(self, mock_apply, mock_update_tag, mock_scan, tmp_path, opts, instance):
        """Test rewrite mode (write_mode=1) calls refresh_series."""
        show_path = tmp_path / "TestShow"
        season_path = show_path / "Season 01"
        season_path.mkdir(parents=True)
        (show_path / "tvshow.nfo").write_text("<tvshow><genre>Drama</genre></tvshow>")

        instance.root_path = str(tmp_path)
        opts.write_mode = 1
        client = Mock()
        client.get_series_by_path.return_value = {"id": 123, "originalLanguage": "Japanese"}
        mock_scan.return_value = (instance.tags.dub, {"Season 01": {"status": "fully-dub"}})
        taggarr_data = {"series": {}}

        tv.process_all(client, instance, opts, taggarr_data)

        client.refresh_series.assert_called_once_with(123, False)

    @patch("taggarr.processors.tv._scan_show")
    @patch("taggarr.processors.tv.nfo.update_tag")
    @patch("taggarr.processors.tv._apply_tags")
    def test_no_nfo_update_when_no_tag(self, mock_apply, mock_update_tag, mock_scan, tmp_path, opts, instance):
        """Test NFO is not updated when tag is None (original only)."""
        show_path = tmp_path / "TestShow"
        season_path = show_path / "Season 01"
        season_path.mkdir(parents=True)
        (show_path / "tvshow.nfo").write_text("<tvshow><genre>Drama</genre></tvshow>")

        instance.root_path = str(tmp_path)
        client = Mock()
        client.get_series_by_path.return_value = {"id": 123, "originalLanguage": "Japanese"}
        mock_scan.return_value = (None, {"Season 01": {"status": "original"}})
        taggarr_data = {"series": {}}

        tv.process_all(client, instance, opts, taggarr_data)

        mock_update_tag.assert_not_called()

    @patch("taggarr.processors.tv._scan_show")
    @patch("taggarr.processors.tv.nfo.update_tag")
    @patch("taggarr.processors.tv._apply_tags")
    def test_uses_instance_quick_mode(self, mock_apply, mock_update_tag, mock_scan, tmp_path, opts, instance):
        """Test instance-level quick_mode is used."""
        show_path = tmp_path / "TestShow"
        season_path = show_path / "Season 01"
        season_path.mkdir(parents=True)
        (show_path / "tvshow.nfo").write_text("<tvshow><genre>Drama</genre></tvshow>")

        instance.root_path = str(tmp_path)
        instance.quick_mode = True
        opts.quick = False  # CLI not set, but instance is
        client = Mock()
        client.get_series_by_path.return_value = {"id": 123, "originalLanguage": "Japanese"}
        mock_scan.return_value = (instance.tags.dub, {"Season 01": {"status": "fully-dub"}})
        taggarr_data = {"series": {}}

        tv.process_all(client, instance, opts, taggarr_data)

        # The quick flag should be True due to instance.quick_mode
        # _scan_show is called with positional args: (show_path, series, instance, language_codes, quick)
        mock_scan.assert_called_once()
        call_args = mock_scan.call_args[0]
        quick_arg = call_args[4]  # 5th positional arg is quick
        assert quick_arg is True

    @patch("taggarr.processors.tv._scan_show")
    @patch("taggarr.processors.tv.nfo.update_tag")
    @patch("taggarr.processors.tv._apply_tags")
    def test_uses_instance_dry_run(self, mock_apply, mock_update_tag, mock_scan, tmp_path, opts, instance):
        """Test instance-level dry_run is used."""
        show_path = tmp_path / "TestShow"
        season_path = show_path / "Season 01"
        season_path.mkdir(parents=True)
        (show_path / "tvshow.nfo").write_text("<tvshow><genre>Drama</genre></tvshow>")

        instance.root_path = str(tmp_path)
        instance.dry_run = True
        opts.dry_run = False  # CLI not set, but instance is
        client = Mock()
        client.get_series_by_path.return_value = {"id": 123, "originalLanguage": "Japanese"}
        mock_scan.return_value = (instance.tags.dub, {"Season 01": {"status": "fully-dub"}})
        taggarr_data = {"series": {}}

        tv.process_all(client, instance, opts, taggarr_data)

        # dry_run should be True in _apply_tags call
        mock_apply.assert_called_once()
        assert mock_apply.call_args[0][4] is True  # dry_run argument

    @patch("taggarr.processors.tv._scan_show")
    @patch("taggarr.processors.tv.nfo.update_tag")
    @patch("taggarr.processors.tv._apply_tags")
    def test_calculates_max_mtime(self, mock_apply, mock_update_tag, mock_scan, tmp_path, opts, instance):
        """Test correct mtime is calculated from seasons."""
        show_path = tmp_path / "TestShow"
        season1 = show_path / "Season 01"
        season2 = show_path / "Season 02"
        season1.mkdir(parents=True)
        season2.mkdir(parents=True)
        (show_path / "tvshow.nfo").write_text("<tvshow><genre>Drama</genre></tvshow>")
        # Non-season dir should be ignored
        (show_path / "Extras").mkdir()

        instance.root_path = str(tmp_path)
        client = Mock()
        client.get_series_by_path.return_value = {"id": 123, "originalLanguage": "Japanese"}
        mock_scan.return_value = (instance.tags.dub, {"Season 01": {}, "Season 02": {}})
        taggarr_data = {"series": {}}

        result = tv.process_all(client, instance, opts, taggarr_data)

        # Verify mtime is stored
        assert "last_modified" in result["series"][str(show_path)]
