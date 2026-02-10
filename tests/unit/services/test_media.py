"""Tests for taggarr.services.media module."""

import logging
import pytest
from unittest.mock import Mock, patch

from taggarr.services import media


class MockTrack:
    """Mock mediainfo track."""
    def __init__(self, track_type, language=None, title=None):
        self.track_type = track_type
        self.language = language
        self.title = title


class MockMediaInfo:
    """Mock MediaInfo result."""
    def __init__(self, tracks):
        self.tracks = tracks


class TestAnalyzeAudio:
    """Tests for analyze_audio function."""

    @patch("taggarr.services.media.MediaInfo.parse")
    def test_returns_language_codes_from_audio_tracks(self, mock_parse):
        mock_parse.return_value = MockMediaInfo([
            MockTrack("Audio", language="en"),
            MockTrack("Audio", language="ja"),
            MockTrack("Video"),  # Should be ignored
        ])

        result = media.analyze_audio("/path/to/video.mkv")

        assert sorted(result) == ["en", "ja"]

    @patch("taggarr.services.media.MediaInfo.parse")
    def test_returns_empty_list_on_no_audio_tracks(self, mock_parse):
        mock_parse.return_value = MockMediaInfo([
            MockTrack("Video"),
        ])

        result = media.analyze_audio("/path/to/video.mkv")

        assert result == []

    @patch("taggarr.services.media.MediaInfo.parse")
    def test_uses_fallback_for_empty_title_track(self, mock_parse):
        mock_parse.return_value = MockMediaInfo([
            MockTrack("Audio", language="", title=""),
        ])

        result = media.analyze_audio("/path/to/video.mkv")

        assert "__fallback_original__" in result

    @patch("taggarr.services.media.MediaInfo.parse")
    def test_uses_fallback_for_track_1_title(self, mock_parse):
        mock_parse.return_value = MockMediaInfo([
            MockTrack("Audio", language="", title="Track 1"),
        ])

        result = media.analyze_audio("/path/to/video.mkv")

        assert "__fallback_original__" in result

    @patch("taggarr.services.media.MediaInfo.parse")
    def test_uses_fallback_for_audio_1_title(self, mock_parse):
        mock_parse.return_value = MockMediaInfo([
            MockTrack("Audio", language=None, title="Audio 1"),
        ])

        result = media.analyze_audio("/path/to/video.mkv")

        assert "__fallback_original__" in result

    @patch("taggarr.services.media.MediaInfo.parse")
    def test_no_fallback_for_non_first_unlabeled_track(self, mock_parse):
        """Non-first audio track without language should not trigger fallback."""
        mock_parse.return_value = MockMediaInfo([
            MockTrack("Audio", language="en"),
            MockTrack("Audio", language="", title="Track 1"),
        ])

        result = media.analyze_audio("/path/to/video.mkv")

        assert "en" in result
        assert "__fallback_original__" not in result

    @patch("taggarr.services.media.MediaInfo.parse")
    def test_fallback_for_first_unlabeled_with_labeled_second(self, mock_parse):
        """First track unlabeled, second labeled - fallback applies to first."""
        mock_parse.return_value = MockMediaInfo([
            MockTrack("Audio", language="", title=""),
            MockTrack("Audio", language="ja"),
        ])

        result = media.analyze_audio("/path/to/video.mkv")

        assert "__fallback_original__" in result
        assert "ja" in result

    @patch("taggarr.services.media.MediaInfo.parse")
    def test_returns_empty_list_on_parse_error(self, mock_parse, caplog):
        caplog.set_level(logging.WARNING)
        mock_parse.side_effect = RuntimeError("Parse error")

        result = media.analyze_audio("/path/to/video.mkv")

        assert result == []
        assert "Audio analysis failed" in caplog.text

    @patch("taggarr.services.media.MediaInfo.parse")
    def test_normalizes_language_to_lowercase(self, mock_parse):
        mock_parse.return_value = MockMediaInfo([
            MockTrack("Audio", language="EN"),
            MockTrack("Audio", language="  JA  "),
        ])

        result = media.analyze_audio("/path/to/video.mkv")

        assert "en" in result
        assert "ja" in result

    @patch("taggarr.services.media.MediaInfo.parse")
    def test_deduplicates_languages(self, mock_parse):
        mock_parse.return_value = MockMediaInfo([
            MockTrack("Audio", language="en"),
            MockTrack("Audio", language="en"),
        ])

        result = media.analyze_audio("/path/to/video.mkv")

        assert result.count("en") == 1

    @patch("taggarr.services.media.MediaInfo.parse")
    def test_logs_debug_for_fallback_detection(self, mock_parse, caplog):
        caplog.set_level(logging.DEBUG, logger="taggarr")
        mock_parse.return_value = MockMediaInfo([
            MockTrack("Audio", language="", title=""),
        ])

        media.analyze_audio("/path/to/video.mkv")

        assert "Fallback language detection" in caplog.text

    @patch("taggarr.services.media.MediaInfo.parse")
    def test_does_not_use_fallback_for_commentary_track(self, mock_parse):
        """First track with commentary title should not trigger fallback."""
        mock_parse.return_value = MockMediaInfo([
            MockTrack("Audio", language="", title="Commentary"),
        ])

        result = media.analyze_audio("/path/to/video.mkv")

        assert "__fallback_original__" not in result
        assert result == []

    @patch("taggarr.services.media.MediaInfo.parse")
    def test_does_not_use_fallback_for_directors_commentary(self, mock_parse):
        """Director's commentary at first position should not trigger fallback."""
        mock_parse.return_value = MockMediaInfo([
            MockTrack("Audio", language="", title="Director's Commentary"),
        ])

        result = media.analyze_audio("/path/to/video.mkv")

        assert "__fallback_original__" not in result
        assert result == []
