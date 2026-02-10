"""Tests for taggarr.storage.json_store module."""

import json
import logging
import os
import pytest

from taggarr.storage import json_store


class TestLoad:
    """Tests for load function."""

    def test_returns_empty_dict_for_none_path(self):
        result = json_store.load(None)
        assert result == {"series": {}}

    def test_returns_empty_dict_for_nonexistent_file(self, tmp_path, caplog):
        caplog.set_level(logging.INFO)
        result = json_store.load(str(tmp_path / "nonexistent.json"))
        assert result == {"series": {}}
        assert "starting fresh" in caplog.text

    def test_loads_existing_json_file(self, tmp_path, caplog):
        caplog.set_level(logging.INFO)
        json_path = tmp_path / "taggarr.json"
        data = {"series": {"show1": {"tag": "dub"}}}
        json_path.write_text(json.dumps(data))

        result = json_store.load(str(json_path))

        assert result["series"]["show1"]["tag"] == "dub"
        assert "taggarr.json found" in caplog.text

    def test_uses_custom_key(self, tmp_path):
        json_path = tmp_path / "taggarr.json"
        data = {"movies": {"movie1": {"tag": "dub"}}}
        json_path.write_text(json.dumps(data))

        result = json_store.load(str(json_path), key="movies")

        assert "movies" in result

    def test_returns_empty_dict_for_none_path_with_custom_key(self):
        result = json_store.load(None, key="movies")
        assert result == {"movies": {}}

    def test_handles_corrupted_json(self, tmp_path, caplog):
        caplog.set_level(logging.WARNING)
        json_path = tmp_path / "taggarr.json"
        json_path.write_text("not valid json {{{")

        result = json_store.load(str(json_path))

        assert result == {"series": {}}
        # Should have created backup
        assert (tmp_path / "taggarr.json.bak").exists()
        assert "corrupted" in caplog.text


class TestSave:
    """Tests for save function."""

    def test_does_nothing_for_none_path(self, tmp_path):
        json_store.save(None, {"series": {}})
        # No error should be raised

    def test_saves_data_to_file(self, tmp_path):
        json_path = tmp_path / "taggarr.json"
        data = {"series": {"show1": {"tag": "dub"}}}

        json_store.save(str(json_path), data)

        assert json_path.exists()
        loaded = json.loads(json_path.read_text())
        assert loaded["series"]["show1"]["tag"] == "dub"

    def test_adds_version_to_saved_data(self, tmp_path):
        json_path = tmp_path / "taggarr.json"
        data = {"series": {}}

        json_store.save(str(json_path), data)

        loaded = json.loads(json_path.read_text())
        assert "version" in loaded

    def test_version_is_first_key(self, tmp_path):
        json_path = tmp_path / "taggarr.json"
        data = {"series": {"a": 1}}

        json_store.save(str(json_path), data)

        content = json_path.read_text()
        # Version should appear before series in the JSON
        assert content.index('"version"') < content.index('"series"')

    def test_handles_save_error(self, tmp_path, caplog):
        caplog.set_level(logging.WARNING)
        # Try to write to a directory (should fail)
        dir_path = tmp_path / "testdir"
        dir_path.mkdir()

        json_store.save(str(dir_path), {"series": {}})

        assert "Failed to save" in caplog.text


class TestCompactLists:
    """Tests for _compact_lists function."""

    def test_compacts_episode_lists(self):
        raw = '[\n  "E01",\n  "E02",\n  "E03"\n]'
        result = json_store._compact_lists(raw)
        assert result == '["E01", "E02", "E03"]'

    def test_compacts_dub_language_lists(self):
        raw = '"dub": [\n  "en",\n  "ja"\n]'
        result = json_store._compact_lists(raw)
        assert '"dub": ["en", "ja"]' in result

    def test_compacts_original_dub_list(self):
        raw = '"original_dub": [\n  "E01",\n  "E02"\n]'
        result = json_store._compact_lists(raw)
        assert '"original_dub": ["E01", "E02"]' in result

    def test_compacts_missing_dub_list(self):
        raw = '"missing_dub": [\n  "E03",\n  "E04"\n]'
        result = json_store._compact_lists(raw)
        assert '"missing_dub": ["E03", "E04"]' in result

    def test_compacts_unexpected_languages_list(self):
        raw = '"unexpected_languages": [\n  "de",\n  "fr"\n]'
        result = json_store._compact_lists(raw)
        assert '"unexpected_languages": ["de", "fr"]' in result

    def test_compacts_languages_list(self):
        raw = '"languages": [\n  "en",\n  "es"\n]'
        result = json_store._compact_lists(raw)
        assert '"languages": ["en", "es"]' in result

    def test_preserves_other_formatting(self):
        raw = '{\n  "name": "test",\n  "value": 123\n}'
        result = json_store._compact_lists(raw)
        assert result == raw


class TestCleanupOrphans:
    """Tests for cleanup_orphans function."""

    def test_removes_orphaned_entries(self, caplog):
        caplog.set_level(logging.INFO)
        data = {"series": {
            "/tv/show_a": {"tag": "dub"},
            "/tv/show_b": {"tag": "none"},
        }}
        valid_paths = {"/tv/show_a"}

        removed = json_store.cleanup_orphans(data, "series", valid_paths)

        assert removed == 1
        assert "/tv/show_a" in data["series"]
        assert "/tv/show_b" not in data["series"]
        assert "orphaned" in caplog.text

    def test_returns_zero_when_no_orphans(self):
        data = {"series": {"/tv/show_a": {"tag": "dub"}}}
        valid_paths = {"/tv/show_a"}

        removed = json_store.cleanup_orphans(data, "series", valid_paths)

        assert removed == 0

    def test_handles_empty_data(self):
        data = {"series": {}}
        valid_paths = {"/tv/show_a"}

        removed = json_store.cleanup_orphans(data, "series", valid_paths)

        assert removed == 0

    def test_works_with_movies_key(self):
        data = {"movies": {
            "/movies/a": {"tag": "dub"},
            "/movies/b": {"tag": "dub"},
        }}
        valid_paths = set()

        removed = json_store.cleanup_orphans(data, "movies", valid_paths)

        assert removed == 2
        assert data["movies"] == {}


class TestCleanupOrphansForRoot:
    """Tests for cleanup_orphans_for_root function."""

    def test_removes_orphans_from_root(self, tmp_path, caplog):
        caplog.set_level(logging.INFO)
        # Create one directory on disk
        (tmp_path / "show_a").mkdir()
        # Data has two entries, one is orphaned
        show_a_path = str(tmp_path / "show_a")
        data = {"series": {
            show_a_path: {"tag": "dub"},
            "/nonexistent/show_b": {"tag": "none"},
        }}

        removed = json_store.cleanup_orphans_for_root(data, "series", str(tmp_path))

        assert removed == 1
        assert show_a_path in data["series"]
        assert "/nonexistent/show_b" not in data["series"]

    def test_returns_zero_on_oserror(self, tmp_path, caplog):
        caplog.set_level(logging.WARNING)
        data = {"series": {"/tv/show_a": {"tag": "dub"}}}

        removed = json_store.cleanup_orphans_for_root(data, "series", "/nonexistent/root")

        assert removed == 0
        assert "Could not list" in caplog.text
        # Data should be preserved (not lost)
        assert "/tv/show_a" in data["series"]

    def test_returns_zero_when_no_orphans(self, tmp_path):
        show_path = str(tmp_path / "show_a")
        (tmp_path / "show_a").mkdir()
        data = {"series": {show_path: {"tag": "dub"}}}

        removed = json_store.cleanup_orphans_for_root(data, "series", str(tmp_path))

        assert removed == 0


class TestAtomicSave:
    """Tests for atomic save using write-to-temp-then-rename."""

    def test_no_tmp_file_after_save(self, tmp_path):
        json_path = tmp_path / "taggarr.json"
        data = {"series": {"show": {"tag": "dub"}}}

        json_store.save(str(json_path), data)

        assert json_path.exists()
        assert not (tmp_path / "taggarr.json.tmp").exists()

    def test_save_is_valid_json(self, tmp_path):
        json_path = tmp_path / "taggarr.json"
        data = {"series": {"show": {"tag": "dub"}}}

        json_store.save(str(json_path), data)

        loaded = json.loads(json_path.read_text())
        assert loaded["series"]["show"]["tag"] == "dub"
