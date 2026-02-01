"""Tests for taggarr.processors.movies module."""

import logging
import os
import pytest
from unittest.mock import Mock, patch
from types import SimpleNamespace

from taggarr.processors import movies
from taggarr.config_schema import InstanceConfig, TagsConfig


@pytest.fixture
def instance():
    """Radarr instance config."""
    return InstanceConfig(
        name="test",
        type="radarr",
        url="http://radarr:7878",
        api_key="key",
        root_path="/media/movies",
        target_languages=["en"],
        tags=TagsConfig(),
        dry_run=False,
        quick_mode=False,
        target_genre=None,
    )


class TestDetermineTag:
    """Tests for _determine_tag function."""

    def test_returns_none_for_none_scan_result(self, instance):
        result = movies._determine_tag(None, instance, {"en"})
        assert result is None

    def test_returns_none_for_fallback_original(self, instance, caplog):
        caplog.set_level(logging.INFO)
        scan_result = {
            "languages": ["__fallback_original__"],
            "original_codes": {"ja"},
        }

        result = movies._determine_tag(scan_result, instance, {"en"})

        assert result is None
        assert "assuming original" in caplog.text

    def test_returns_dub_when_all_targets_present(self, instance):
        scan_result = {
            "languages": ["en", "ja"],
            "original_codes": {"ja", "jpn", "japanese"},
        }

        result = movies._determine_tag(scan_result, instance, {"en", "eng", "english"})

        assert result == "dub"

    def test_returns_wrong_when_unexpected_language(self, instance):
        scan_result = {
            "languages": ["en", "de"],  # German is unexpected
            "original_codes": {"ja", "jpn"},
        }

        result = movies._determine_tag(scan_result, instance, {"en", "eng"})

        assert result == "wrong-dub"

    def test_returns_none_when_original_only(self, instance):
        scan_result = {
            "languages": ["ja"],
            "original_codes": {"ja", "jpn", "japanese"},
        }

        result = movies._determine_tag(scan_result, instance, {"en"})

        assert result is None

    def test_returns_none_when_missing_some_targets(self, instance):
        """Test that missing target languages results in no tag (not wrong)."""
        instance.target_languages = ["en", "de"]  # Expect both
        scan_result = {
            "languages": ["en", "ja"],  # Has en but not de
            "original_codes": {"ja"},
        }

        result = movies._determine_tag(scan_result, instance, {"en", "de"})

        assert result is None  # Not fully dubbed, no wrong language


class TestFindNfo:
    """Tests for _find_nfo function."""

    def test_finds_movie_nfo(self, tmp_path):
        movie_path = tmp_path / "Inception (2010)"
        movie_path.mkdir()
        (movie_path / "movie.nfo").write_text("<movie/>")

        result = movies._find_nfo(str(movie_path), "Inception (2010)")

        assert result is not None
        assert result.endswith("movie.nfo")

    def test_finds_named_nfo(self, tmp_path):
        movie_path = tmp_path / "Inception (2010)"
        movie_path.mkdir()
        (movie_path / "Inception (2010).nfo").write_text("<movie/>")

        result = movies._find_nfo(str(movie_path), "Inception (2010)")

        assert result is not None
        assert "Inception" in result

    def test_returns_none_when_no_nfo(self, tmp_path):
        movie_path = tmp_path / "Inception (2010)"
        movie_path.mkdir()

        result = movies._find_nfo(str(movie_path), "Inception (2010)")

        assert result is None

    def test_prefers_movie_nfo_over_named(self, tmp_path):
        movie_path = tmp_path / "Inception (2010)"
        movie_path.mkdir()
        (movie_path / "movie.nfo").write_text("<movie/>")
        (movie_path / "Inception (2010).nfo").write_text("<movie/>")

        result = movies._find_nfo(str(movie_path), "Inception (2010)")

        assert result.endswith("movie.nfo")


class TestScanMovie:
    """Tests for _scan_movie function."""

    @patch("taggarr.processors.movies.media.analyze_audio")
    def test_returns_scan_result_for_valid_movie(self, mock_analyze, tmp_path, instance):
        movie_path = tmp_path / "Inception (2010)"
        movie_path.mkdir()
        video_file = movie_path / "Inception.2010.mkv"
        video_file.write_bytes(b"x" * 1000)

        mock_analyze.return_value = ["en", "ja"]
        movie_meta = {"originalLanguage": {"name": "English"}}

        result = movies._scan_movie(str(movie_path), movie_meta, instance, {"en"})

        assert result is not None
        assert "en" in result["languages"]
        assert result["original_language"] == "english"

    @patch("taggarr.processors.movies.media.analyze_audio")
    def test_returns_none_when_no_video_files(self, mock_analyze, tmp_path, instance, caplog):
        caplog.set_level(logging.WARNING)
        movie_path = tmp_path / "Empty Movie"
        movie_path.mkdir()

        movie_meta = {"originalLanguage": "English"}

        result = movies._scan_movie(str(movie_path), movie_meta, instance, {"en"})

        assert result is None
        assert "No video files" in caplog.text

    @patch("taggarr.processors.movies.media.analyze_audio")
    def test_ignores_sample_files(self, mock_analyze, tmp_path, instance):
        movie_path = tmp_path / "Movie"
        movie_path.mkdir()
        (movie_path / "sample.mkv").write_bytes(b"x" * 100)
        (movie_path / "Movie.mkv").write_bytes(b"x" * 1000)

        mock_analyze.return_value = ["en"]
        movie_meta = {"originalLanguage": "English"}

        result = movies._scan_movie(str(movie_path), movie_meta, instance, {"en"})

        # Should have scanned the larger file, not the sample
        assert "Movie.mkv" in result["file"]

    @patch("taggarr.processors.movies.media.analyze_audio")
    def test_scans_largest_video_file(self, mock_analyze, tmp_path, instance):
        movie_path = tmp_path / "Movie"
        movie_path.mkdir()
        (movie_path / "small.mkv").write_bytes(b"x" * 100)
        (movie_path / "main.mkv").write_bytes(b"x" * 10000)
        (movie_path / "medium.mkv").write_bytes(b"x" * 1000)

        mock_analyze.return_value = ["en"]
        movie_meta = {"originalLanguage": "English"}

        result = movies._scan_movie(str(movie_path), movie_meta, instance, {"en"})

        assert result["file"] == "main.mkv"

    @patch("taggarr.processors.movies.media.analyze_audio")
    def test_handles_string_original_language(self, mock_analyze, tmp_path, instance):
        movie_path = tmp_path / "Movie"
        movie_path.mkdir()
        (movie_path / "movie.mkv").write_bytes(b"x" * 1000)

        mock_analyze.return_value = ["en"]
        movie_meta = {"originalLanguage": "Japanese"}

        result = movies._scan_movie(str(movie_path), movie_meta, instance, {"en"})

        assert result["original_language"] == "japanese"

    @patch("taggarr.processors.movies.media.analyze_audio")
    def test_ignores_extras_directory(self, mock_analyze, tmp_path, instance):
        movie_path = tmp_path / "Movie"
        movie_path.mkdir()
        (movie_path / "movie.mkv").write_bytes(b"x" * 1000)
        extras = movie_path / "Extras"
        extras.mkdir()
        (extras / "behind.mkv").write_bytes(b"x" * 2000)  # Bigger but in extras

        mock_analyze.return_value = ["en"]
        movie_meta = {"originalLanguage": "English"}

        result = movies._scan_movie(str(movie_path), movie_meta, instance, {"en"})

        # Should have scanned main movie, not extras
        assert result["file"] == "movie.mkv"

    @patch("taggarr.processors.movies.media.analyze_audio")
    def test_ignores_featurettes_in_filename(self, mock_analyze, tmp_path, instance):
        movie_path = tmp_path / "Movie"
        movie_path.mkdir()
        (movie_path / "movie.mkv").write_bytes(b"x" * 1000)
        (movie_path / "movie-featurettes.mkv").write_bytes(b"x" * 2000)

        mock_analyze.return_value = ["en"]
        movie_meta = {"originalLanguage": "English"}

        result = movies._scan_movie(str(movie_path), movie_meta, instance, {"en"})

        assert result["file"] == "movie.mkv"


class TestProcessAll:
    """Tests for process_all function."""

    @patch("taggarr.processors.movies._scan_movie")
    @patch("taggarr.processors.movies._determine_tag")
    def test_skips_non_directory(self, mock_tag, mock_scan, tmp_path, instance):
        instance.root_path = str(tmp_path)
        (tmp_path / "some_file.txt").write_text("not a directory")

        client = Mock()
        opts = SimpleNamespace(quick=False, dry_run=False, write_mode=0)
        taggarr_data = {"movies": {}}

        movies.process_all(client, instance, opts, taggarr_data)

        mock_scan.assert_not_called()

    @patch("taggarr.processors.movies._scan_movie")
    @patch("taggarr.processors.movies._determine_tag")
    def test_skips_hidden_folders(self, mock_tag, mock_scan, tmp_path, instance):
        instance.root_path = str(tmp_path)
        (tmp_path / ".hidden_folder").mkdir()

        client = Mock()
        opts = SimpleNamespace(quick=False, dry_run=False, write_mode=0)
        taggarr_data = {"movies": {}}

        movies.process_all(client, instance, opts, taggarr_data)

        mock_scan.assert_not_called()

    @patch("taggarr.processors.movies._scan_movie")
    def test_skips_unchanged_movies(self, mock_scan, tmp_path, instance, caplog):
        caplog.set_level(logging.INFO)
        instance.root_path = str(tmp_path)
        movie_path = tmp_path / "Movie (2020)"
        movie_path.mkdir()
        (movie_path / "movie.mkv").write_bytes(b"x" * 100)

        # Mark as already scanned with future mtime
        taggarr_data = {
            "movies": {
                str(movie_path): {"last_modified": 9999999999}
            }
        }

        client = Mock()
        opts = SimpleNamespace(quick=False, dry_run=False, write_mode=0)

        movies.process_all(client, instance, opts, taggarr_data)

        mock_scan.assert_not_called()
        assert "no changes" in caplog.text

    @patch("taggarr.processors.movies._scan_movie")
    def test_skips_movie_without_radarr_metadata(self, mock_scan, tmp_path, instance, caplog):
        caplog.set_level(logging.WARNING)
        instance.root_path = str(tmp_path)
        movie_path = tmp_path / "Movie (2020)"
        movie_path.mkdir()
        (movie_path / "movie.mkv").write_bytes(b"x" * 100)

        client = Mock()
        client.get_movie_by_path.return_value = None
        opts = SimpleNamespace(quick=False, dry_run=False, write_mode=0)
        taggarr_data = {"movies": {}}

        movies.process_all(client, instance, opts, taggarr_data)

        assert "No Radarr metadata" in caplog.text

    @patch("taggarr.processors.movies._scan_movie")
    def test_skips_not_downloaded(self, mock_scan, tmp_path, instance, caplog):
        caplog.set_level(logging.DEBUG)
        instance.root_path = str(tmp_path)
        movie_path = tmp_path / "Movie (2020)"
        movie_path.mkdir()
        (movie_path / "movie.mkv").write_bytes(b"x" * 100)

        client = Mock()
        client.get_movie_by_path.return_value = {"id": 1, "hasFile": False}
        opts = SimpleNamespace(quick=False, dry_run=False, write_mode=0)
        taggarr_data = {"movies": {}}

        movies.process_all(client, instance, opts, taggarr_data)

        mock_scan.assert_not_called()

    @patch("taggarr.processors.movies._scan_movie")
    def test_skips_genre_mismatch(self, mock_scan, tmp_path, instance, caplog):
        caplog.set_level(logging.INFO)
        instance.root_path = str(tmp_path)
        instance.target_genre = "anime"
        movie_path = tmp_path / "Movie (2020)"
        movie_path.mkdir()
        (movie_path / "movie.mkv").write_bytes(b"x" * 100)

        client = Mock()
        client.get_movie_by_path.return_value = {
            "id": 1, "hasFile": True, "genres": ["Action", "Drama"]
        }
        opts = SimpleNamespace(quick=False, dry_run=False, write_mode=0)
        taggarr_data = {"movies": {}}

        movies.process_all(client, instance, opts, taggarr_data)

        mock_scan.assert_not_called()
        assert "genre mismatch" in caplog.text

    @patch("taggarr.processors.movies._scan_movie")
    @patch("taggarr.processors.movies._determine_tag")
    def test_processes_with_genre_match(self, mock_tag, mock_scan, tmp_path, instance):
        """Test processing proceeds when genre filter matches."""
        instance.root_path = str(tmp_path)
        instance.target_genre = "anime"
        movie_path = tmp_path / "Movie (2020)"
        movie_path.mkdir()
        (movie_path / "movie.mkv").write_bytes(b"x" * 100)

        mock_scan.return_value = {
            "file": "movie.mkv",
            "languages": ["en", "ja"],
            "original_language": "japanese",
            "original_codes": {"ja"},
        }
        mock_tag.return_value = "dub"

        client = Mock()
        client.get_movie_by_path.return_value = {
            "id": 1, "hasFile": True, "genres": ["Anime", "Action"]
        }
        opts = SimpleNamespace(quick=False, dry_run=False, write_mode=0)
        taggarr_data = {"movies": {}}

        movies.process_all(client, instance, opts, taggarr_data)

        mock_scan.assert_called_once()

    @patch("taggarr.processors.movies._scan_movie")
    @patch("taggarr.processors.movies._determine_tag")
    def test_remove_mode_handles_missing_movie_in_data(self, mock_tag, mock_scan, tmp_path, instance):
        """Test remove mode when movie is not already in taggarr_data."""
        instance.root_path = str(tmp_path)
        movie_path = tmp_path / "Movie (2020)"
        movie_path.mkdir()
        (movie_path / "movie.mkv").write_bytes(b"x" * 100)

        client = Mock()
        client.get_movie_by_path.return_value = {"id": 42, "hasFile": True}
        opts = SimpleNamespace(quick=False, dry_run=False, write_mode=2)
        taggarr_data = {"movies": {}}  # Movie not in data

        result = movies.process_all(client, instance, opts, taggarr_data)

        assert client.remove_tag.call_count == 2
        # Should not fail even though movie wasn't in data
        assert str(movie_path) not in result["movies"]

    @patch("taggarr.processors.movies._scan_movie")
    def test_skips_movie_without_id(self, mock_scan, tmp_path, instance, caplog):
        caplog.set_level(logging.WARNING)
        instance.root_path = str(tmp_path)
        movie_path = tmp_path / "Movie (2020)"
        movie_path.mkdir()
        (movie_path / "movie.mkv").write_bytes(b"x" * 100)

        client = Mock()
        client.get_movie_by_path.return_value = {"hasFile": True}  # No id
        opts = SimpleNamespace(quick=False, dry_run=False, write_mode=0)
        taggarr_data = {"movies": {}}

        movies.process_all(client, instance, opts, taggarr_data)

        assert "No Radarr ID" in caplog.text

    @patch("taggarr.processors.movies._scan_movie")
    @patch("taggarr.processors.movies._determine_tag")
    def test_remove_mode_deletes_tags(self, mock_tag, mock_scan, tmp_path, instance, caplog):
        caplog.set_level(logging.INFO)
        instance.root_path = str(tmp_path)
        movie_path = tmp_path / "Movie (2020)"
        movie_path.mkdir()
        (movie_path / "movie.mkv").write_bytes(b"x" * 100)

        client = Mock()
        client.get_movie_by_path.return_value = {"id": 42, "hasFile": True}
        opts = SimpleNamespace(quick=False, dry_run=False, write_mode=2)
        taggarr_data = {"movies": {str(movie_path): {"tag": "dub"}}}

        result = movies.process_all(client, instance, opts, taggarr_data)

        assert client.remove_tag.call_count == 2
        assert str(movie_path) not in result["movies"]

    @patch("taggarr.processors.movies._scan_movie")
    @patch("taggarr.processors.movies._determine_tag")
    def test_applies_dub_tag(self, mock_tag, mock_scan, tmp_path, instance):
        instance.root_path = str(tmp_path)
        movie_path = tmp_path / "Movie (2020)"
        movie_path.mkdir()
        (movie_path / "movie.mkv").write_bytes(b"x" * 100)

        mock_scan.return_value = {
            "file": "movie.mkv",
            "languages": ["en"],
            "original_language": "japanese",
            "original_codes": {"ja"},
            "last_modified": 12345.0,
        }
        mock_tag.return_value = "dub"

        client = Mock()
        client.get_movie_by_path.return_value = {"id": 42, "hasFile": True}
        opts = SimpleNamespace(quick=False, dry_run=False, write_mode=0)
        taggarr_data = {"movies": {}}

        result = movies.process_all(client, instance, opts, taggarr_data)

        client.add_tag.assert_called_once_with(42, "dub", False)
        client.remove_tag.assert_called_once_with(42, "wrong-dub", False)

    @patch("taggarr.processors.movies._scan_movie")
    @patch("taggarr.processors.movies._determine_tag")
    def test_applies_wrong_tag(self, mock_tag, mock_scan, tmp_path, instance):
        instance.root_path = str(tmp_path)
        movie_path = tmp_path / "Movie (2020)"
        movie_path.mkdir()
        (movie_path / "movie.mkv").write_bytes(b"x" * 100)

        mock_scan.return_value = {
            "file": "movie.mkv",
            "languages": ["en", "de"],
            "original_language": "japanese",
            "original_codes": {"ja"},
            "last_modified": 12345.0,
        }
        mock_tag.return_value = "wrong-dub"

        client = Mock()
        client.get_movie_by_path.return_value = {"id": 42, "hasFile": True}
        opts = SimpleNamespace(quick=False, dry_run=False, write_mode=0)
        taggarr_data = {"movies": {}}

        movies.process_all(client, instance, opts, taggarr_data)

        client.add_tag.assert_called_once_with(42, "wrong-dub", False)
        client.remove_tag.assert_called_once_with(42, "dub", False)

    @patch("taggarr.processors.movies._scan_movie")
    @patch("taggarr.processors.movies._determine_tag")
    def test_removes_all_tags_for_original(self, mock_tag, mock_scan, tmp_path, instance):
        instance.root_path = str(tmp_path)
        movie_path = tmp_path / "Movie (2020)"
        movie_path.mkdir()
        (movie_path / "movie.mkv").write_bytes(b"x" * 100)

        mock_scan.return_value = {
            "file": "movie.mkv",
            "languages": ["ja"],
            "original_language": "japanese",
            "original_codes": {"ja"},
            "last_modified": 12345.0,
        }
        mock_tag.return_value = None  # Original only

        client = Mock()
        client.get_movie_by_path.return_value = {"id": 42, "hasFile": True}
        opts = SimpleNamespace(quick=False, dry_run=False, write_mode=0)
        taggarr_data = {"movies": {}}

        movies.process_all(client, instance, opts, taggarr_data)

        client.add_tag.assert_not_called()
        assert client.remove_tag.call_count == 2

    @patch("taggarr.processors.movies._scan_movie")
    def test_continues_when_scan_returns_none(self, mock_scan, tmp_path, instance):
        instance.root_path = str(tmp_path)
        movie_path = tmp_path / "Movie (2020)"
        movie_path.mkdir()
        (movie_path / "movie.mkv").write_bytes(b"x" * 100)

        mock_scan.return_value = None  # No video files

        client = Mock()
        client.get_movie_by_path.return_value = {"id": 42, "hasFile": True}
        opts = SimpleNamespace(quick=False, dry_run=False, write_mode=0)
        taggarr_data = {"movies": {}}

        result = movies.process_all(client, instance, opts, taggarr_data)

        client.add_tag.assert_not_called()
        assert str(movie_path) not in result["movies"]

    @patch("taggarr.processors.movies._scan_movie")
    @patch("taggarr.processors.movies._determine_tag")
    def test_skips_json_files(self, mock_tag, mock_scan, tmp_path, instance):
        """Test skips folders ending with .json suffix."""
        instance.root_path = str(tmp_path)
        (tmp_path / "taggarr.json").mkdir()  # Dir ending in .json

        client = Mock()
        opts = SimpleNamespace(quick=False, dry_run=False, write_mode=0)
        taggarr_data = {"movies": {}}

        movies.process_all(client, instance, opts, taggarr_data)

        mock_scan.assert_not_called()

    @patch("taggarr.processors.movies._scan_movie")
    @patch("taggarr.processors.movies._determine_tag")
    def test_handles_folder_with_no_video_files(self, mock_tag, mock_scan, tmp_path, instance):
        """Test mtime defaults to 0 when no video files exist (ValueError in max)."""
        instance.root_path = str(tmp_path)
        movie_path = tmp_path / "Empty Movie (2020)"
        movie_path.mkdir()
        # Only text files, no videos - causes ValueError in max()

        mock_scan.return_value = {
            "file": "movie.mkv",
            "languages": ["en"],
            "original_language": "japanese",
            "original_codes": {"ja"},
        }
        mock_tag.return_value = "dub"

        client = Mock()
        client.get_movie_by_path.return_value = {"id": 42, "hasFile": True}
        opts = SimpleNamespace(quick=False, dry_run=False, write_mode=0)
        taggarr_data = {"movies": {}}

        result = movies.process_all(client, instance, opts, taggarr_data)

        # Should process with mtime=0
        assert str(movie_path) in result["movies"]
        assert result["movies"][str(movie_path)]["last_modified"] == 0

    @patch("taggarr.processors.movies._scan_movie")
    @patch("taggarr.processors.movies._determine_tag")
    @patch("taggarr.processors.movies.nfo.update_movie_tag")
    def test_updates_nfo_when_tag_is_dub(self, mock_nfo, mock_tag, mock_scan, tmp_path, instance):
        """Test NFO is updated when tag is dub."""
        instance.root_path = str(tmp_path)
        movie_path = tmp_path / "Movie (2020)"
        movie_path.mkdir()
        (movie_path / "movie.mkv").write_bytes(b"x" * 100)
        (movie_path / "movie.nfo").write_text("<movie/>")

        mock_scan.return_value = {
            "file": "movie.mkv",
            "languages": ["en"],
            "original_language": "japanese",
            "original_codes": {"ja"},
        }
        mock_tag.return_value = "dub"

        client = Mock()
        client.get_movie_by_path.return_value = {"id": 42, "hasFile": True}
        opts = SimpleNamespace(quick=False, dry_run=False, write_mode=0)
        taggarr_data = {"movies": {}}

        movies.process_all(client, instance, opts, taggarr_data)

        mock_nfo.assert_called_once()

    @patch("taggarr.processors.movies._scan_movie")
    @patch("taggarr.processors.movies._determine_tag")
    @patch("taggarr.processors.movies.nfo.update_movie_tag")
    def test_updates_nfo_when_tag_is_wrong(self, mock_nfo, mock_tag, mock_scan, tmp_path, instance):
        """Test NFO is updated when tag is wrong-dub."""
        instance.root_path = str(tmp_path)
        movie_path = tmp_path / "Movie (2020)"
        movie_path.mkdir()
        (movie_path / "movie.mkv").write_bytes(b"x" * 100)
        (movie_path / "movie.nfo").write_text("<movie/>")

        mock_scan.return_value = {
            "file": "movie.mkv",
            "languages": ["en", "de"],
            "original_language": "japanese",
            "original_codes": {"ja"},
        }
        mock_tag.return_value = "wrong-dub"

        client = Mock()
        client.get_movie_by_path.return_value = {"id": 42, "hasFile": True}
        opts = SimpleNamespace(quick=False, dry_run=False, write_mode=0)
        taggarr_data = {"movies": {}}

        movies.process_all(client, instance, opts, taggarr_data)

        mock_nfo.assert_called_once()
