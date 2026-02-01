"""Tests for taggarr.languages module."""

import pytest
from taggarr import languages


class TestGetAliases:
    """Tests for get_aliases function."""

    def test_returns_empty_set_for_none(self):
        result = languages.get_aliases(None)
        assert result == set()

    def test_returns_empty_set_for_empty_string(self):
        result = languages.get_aliases("")
        assert result == set()

    def test_returns_aliases_for_alpha2_code(self):
        result = languages.get_aliases("en")
        assert "en" in result
        assert "eng" in result
        assert "english" in result

    def test_returns_aliases_for_alpha3_code(self):
        result = languages.get_aliases("eng")
        assert "en" in result
        assert "eng" in result

    def test_returns_aliases_for_language_name(self):
        result = languages.get_aliases("english")
        assert "en" in result
        assert "eng" in result

    def test_handles_case_insensitivity(self):
        result = languages.get_aliases("ENGLISH")
        assert "en" in result

    def test_includes_regional_variants(self):
        result = languages.get_aliases("en")
        assert "en-us" in result
        assert "en-gb" in result

    def test_returns_empty_set_for_unknown_language(self):
        result = languages.get_aliases("notareallanguage123")
        assert result == set()

    def test_handles_language_without_alpha2(self):
        """Test handling of languages that don't have alpha_2 codes (e.g., Ancient Greek)."""
        result = languages.get_aliases("grc")  # Ancient Greek has alpha_3 but no alpha_2
        assert "grc" in result
        assert "ancient greek (to 1453)" in result


class TestGetPrimaryCode:
    """Tests for get_primary_code function."""

    def test_returns_alpha2_for_language_name(self):
        result = languages.get_primary_code("English")
        assert result == "en"

    def test_returns_alpha2_for_alpha3_code(self):
        result = languages.get_primary_code("eng")
        assert result == "en"

    def test_returns_truncated_for_unknown(self):
        result = languages.get_primary_code("unknown")
        assert result == "un"

    def test_handles_japanese(self):
        result = languages.get_primary_code("Japanese")
        assert result == "ja"


class TestBuildLanguageCodes:
    """Tests for build_language_codes function."""

    def test_builds_codes_for_single_language(self):
        result = languages.build_language_codes(["en"])
        assert "en" in result
        assert "eng" in result
        assert "english" in result

    def test_builds_codes_for_multiple_languages(self):
        result = languages.build_language_codes(["en", "ja"])
        assert "en" in result
        assert "ja" in result
        assert "japanese" in result

    def test_returns_empty_set_for_empty_list(self):
        result = languages.build_language_codes([])
        assert result == set()
