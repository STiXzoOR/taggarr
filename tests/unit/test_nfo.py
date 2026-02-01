"""Tests for taggarr.nfo module."""

import logging
import pytest
import xml.etree.ElementTree as ET

from taggarr import nfo


class TestSafeParse:
    """Tests for safe_parse function."""

    def test_parses_valid_tvshow_nfo(self, tmp_path):
        nfo_path = tmp_path / "tvshow.nfo"
        nfo_path.write_text("<tvshow><title>Test Show</title></tvshow>")

        root = nfo.safe_parse(str(nfo_path))

        assert root.tag == "tvshow"
        assert root.find("title").text == "Test Show"

    def test_handles_duplicate_closing_tags(self, tmp_path):
        nfo_path = tmp_path / "tvshow.nfo"
        # Corrupted file with duplicate closing tag and garbage after
        nfo_path.write_text("<tvshow><title>Test</title></tvshow></tvshow>garbage")

        root = nfo.safe_parse(str(nfo_path))

        assert root.tag == "tvshow"

    def test_raises_for_invalid_xml(self, tmp_path):
        nfo_path = tmp_path / "bad.nfo"
        nfo_path.write_text("not xml at all")

        with pytest.raises(ET.ParseError):
            nfo.safe_parse(str(nfo_path))

    def test_parses_movie_nfo(self, tmp_path):
        """Test parsing a movie NFO file (no </tvshow> tag)."""
        nfo_path = tmp_path / "movie.nfo"
        nfo_path.write_text("<movie><title>Test Movie</title></movie>")

        root = nfo.safe_parse(str(nfo_path))

        assert root.tag == "movie"


class TestGetGenres:
    """Tests for get_genres function."""

    def test_returns_genres_from_nfo(self, tmp_path):
        nfo_path = tmp_path / "tvshow.nfo"
        nfo_path.write_text("""
<tvshow>
    <genre>Action</genre>
    <genre>Drama</genre>
    <genre>Anime</genre>
</tvshow>
""")

        result = nfo.get_genres(str(nfo_path))

        assert "action" in result
        assert "drama" in result
        assert "anime" in result

    def test_returns_empty_list_for_no_genres(self, tmp_path):
        nfo_path = tmp_path / "tvshow.nfo"
        nfo_path.write_text("<tvshow><title>Test</title></tvshow>")

        result = nfo.get_genres(str(nfo_path))

        assert result == []

    def test_returns_empty_list_on_parse_error(self, tmp_path, caplog):
        caplog.set_level(logging.WARNING)
        nfo_path = tmp_path / "bad.nfo"
        nfo_path.write_text("invalid xml")

        result = nfo.get_genres(str(nfo_path))

        assert result == []
        assert "Genre parsing failed" in caplog.text

    def test_skips_empty_genre_elements(self, tmp_path):
        nfo_path = tmp_path / "tvshow.nfo"
        nfo_path.write_text("<tvshow><genre></genre><genre>Action</genre></tvshow>")

        result = nfo.get_genres(str(nfo_path))

        assert result == ["action"]


class TestUpdateTag:
    """Tests for update_tag function."""

    def test_adds_tag_to_nfo(self, tmp_path, caplog):
        caplog.set_level(logging.INFO)
        nfo_path = tmp_path / "tvshow.nfo"
        nfo_path.write_text("<tvshow><title>Test</title></tvshow>")

        nfo.update_tag(str(nfo_path), "dub")

        content = nfo_path.read_text()
        assert "<tag>dub</tag>" in content
        assert "Updated <tag>dub</tag>" in caplog.text

    def test_removes_existing_managed_tags(self, tmp_path):
        nfo_path = tmp_path / "tvshow.nfo"
        nfo_path.write_text("""<tvshow>
<tag>semi-dub</tag>
<tag>wrong-dub</tag>
<title>Test</title>
</tvshow>""")

        nfo.update_tag(str(nfo_path), "dub")

        content = nfo_path.read_text()
        assert "semi-dub" not in content
        assert "wrong-dub" not in content
        assert "<tag>dub</tag>" in content

    def test_preserves_non_managed_tags(self, tmp_path):
        nfo_path = tmp_path / "tvshow.nfo"
        nfo_path.write_text("""<tvshow>
<tag>custom-tag</tag>
<title>Test</title>
</tvshow>""")

        nfo.update_tag(str(nfo_path), "dub")

        content = nfo_path.read_text()
        assert "custom-tag" in content
        assert "<tag>dub</tag>" in content

    def test_dry_run_does_not_modify_file(self, tmp_path, caplog):
        caplog.set_level(logging.INFO)
        nfo_path = tmp_path / "tvshow.nfo"
        original = "<tvshow><title>Test</title></tvshow>"
        nfo_path.write_text(original)

        nfo.update_tag(str(nfo_path), "dub", dry_run=True)

        assert "<tag>dub</tag>" not in nfo_path.read_text()
        assert "Dry Run" in caplog.text

    def test_handles_parse_error(self, tmp_path, caplog):
        caplog.set_level(logging.WARNING)
        nfo_path = tmp_path / "bad.nfo"
        nfo_path.write_text("invalid xml")

        nfo.update_tag(str(nfo_path), "dub")

        assert "Failed to update <tag>" in caplog.text

    def test_inserts_tag_at_existing_tag_position(self, tmp_path):
        nfo_path = tmp_path / "tvshow.nfo"
        nfo_path.write_text("""<tvshow>
<title>Test</title>
<tag>existing</tag>
</tvshow>""")

        nfo.update_tag(str(nfo_path), "dub")

        content = nfo_path.read_text()
        # New tag should be inserted
        assert "<tag>dub</tag>" in content


class TestUpdateMovieTag:
    """Tests for update_movie_tag function."""

    def test_adds_tag_to_movie_nfo(self, tmp_path, caplog):
        caplog.set_level(logging.INFO)
        nfo_path = tmp_path / "movie.nfo"
        nfo_path.write_text("<movie><title>Test Movie</title></movie>")

        nfo.update_movie_tag(str(nfo_path), "dub")

        content = nfo_path.read_text()
        assert "<tag>dub</tag>" in content
        assert "movie NFO" in caplog.text


class TestUpdateGenre:
    """Tests for update_genre function."""

    def test_adds_dub_genre_when_should_have(self, tmp_path, caplog):
        caplog.set_level(logging.INFO)
        nfo_path = tmp_path / "tvshow.nfo"
        nfo_path.write_text("<tvshow><genre>Action</genre></tvshow>")

        nfo.update_genre(str(nfo_path), should_have_dub=True)

        content = nfo_path.read_text()
        assert "<genre>Dub</genre>" in content
        assert "Adding <genre>Dub</genre>" in caplog.text

    def test_removes_dub_genre_when_should_not_have(self, tmp_path, caplog):
        caplog.set_level(logging.INFO)
        nfo_path = tmp_path / "tvshow.nfo"
        nfo_path.write_text("<tvshow><genre>Dub</genre><genre>Action</genre></tvshow>")

        nfo.update_genre(str(nfo_path), should_have_dub=False)

        content = nfo_path.read_text()
        assert "Dub" not in content
        assert "Action" in content
        assert "Removing <genre>Dub</genre>" in caplog.text

    def test_does_nothing_when_already_correct_has_dub(self, tmp_path):
        nfo_path = tmp_path / "tvshow.nfo"
        original = "<tvshow><genre>Dub</genre></tvshow>"
        nfo_path.write_text(original)

        nfo.update_genre(str(nfo_path), should_have_dub=True)

        # File should be unchanged (already has Dub)
        assert "<genre>Dub</genre>" in nfo_path.read_text()

    def test_does_nothing_when_already_correct_no_dub(self, tmp_path):
        nfo_path = tmp_path / "tvshow.nfo"
        original = "<tvshow><genre>Action</genre></tvshow>"
        nfo_path.write_text(original)

        nfo.update_genre(str(nfo_path), should_have_dub=False)

        # File should be unchanged
        content = nfo_path.read_text()
        assert "Dub" not in content

    def test_dry_run_does_not_modify_file(self, tmp_path, caplog):
        caplog.set_level(logging.INFO)
        nfo_path = tmp_path / "tvshow.nfo"
        original = "<tvshow><genre>Action</genre></tvshow>"
        nfo_path.write_text(original)

        nfo.update_genre(str(nfo_path), should_have_dub=True, dry_run=True)

        assert "Dub" not in nfo_path.read_text()
        assert "Dry Run" in caplog.text

    def test_handles_parse_error(self, tmp_path, caplog):
        caplog.set_level(logging.WARNING)
        nfo_path = tmp_path / "bad.nfo"
        nfo_path.write_text("invalid xml")

        nfo.update_genre(str(nfo_path), should_have_dub=True)

        assert "Failed to update NFO genre" in caplog.text

    def test_adds_dub_genre_with_no_existing_genres(self, tmp_path):
        nfo_path = tmp_path / "tvshow.nfo"
        nfo_path.write_text("<tvshow><title>Test</title></tvshow>")

        nfo.update_genre(str(nfo_path), should_have_dub=True)

        content = nfo_path.read_text()
        assert "<genre>Dub</genre>" in content

    def test_removes_dub_with_case_insensitivity(self, tmp_path):
        """Test that removal works regardless of case."""
        nfo_path = tmp_path / "tvshow.nfo"
        nfo_path.write_text("<tvshow><genre>DUB</genre><genre>Action</genre></tvshow>")

        nfo.update_genre(str(nfo_path), should_have_dub=False)

        content = nfo_path.read_text()
        assert "DUB" not in content
        assert "dub" not in content.lower() or "action" in content.lower()

    def test_dry_run_remove_does_not_modify_file(self, tmp_path, caplog):
        """Test that dry run for removing Dub doesn't modify file."""
        caplog.set_level(logging.INFO)
        nfo_path = tmp_path / "tvshow.nfo"
        original = "<tvshow><genre>Dub</genre><genre>Action</genre></tvshow>"
        nfo_path.write_text(original)

        nfo.update_genre(str(nfo_path), should_have_dub=False, dry_run=True)

        # File should still have Dub
        assert "Dub" in nfo_path.read_text()
        assert "Dry Run" in caplog.text
