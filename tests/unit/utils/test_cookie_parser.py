"""Unit tests for cookie_parser module."""

import tempfile
from pathlib import Path

import pytest
from pydantic import SecretStr

from confluence_markdown_exporter.utils.cookie_parser import parse_cookie_file
from confluence_markdown_exporter.utils.cookie_parser import parse_cookie_string
from confluence_markdown_exporter.utils.cookie_parser import resolve_cookies


class TestParseCookieString:
    """Test cases for parse_cookie_string function."""

    def test_simple_cookie(self) -> None:
        """Test parsing a simple cookie string."""
        result = parse_cookie_string("JSESSIONID=abc123")
        assert result == {"JSESSIONID": "abc123"}

    def test_multiple_cookies(self) -> None:
        """Test parsing multiple cookies."""
        result = parse_cookie_string("JSESSIONID=abc123; token=xyz; session=active")
        assert result == {
            "JSESSIONID": "abc123",
            "token": "xyz",
            "session": "active",
        }

    def test_cookie_with_equals_in_value(self) -> None:
        """Test parsing cookie with equals sign in value."""
        result = parse_cookie_string("token=abc=def=ghi")
        assert result == {"token": "abc=def=ghi"}

    def test_cookie_with_spaces(self) -> None:
        """Test parsing cookies with spaces around separators."""
        result = parse_cookie_string("  JSESSIONID = abc123 ; token = xyz  ")
        assert result == {"JSESSIONID": "abc123", "token": "xyz"}

    def test_empty_cookie_string(self) -> None:
        """Test that empty string raises ValueError."""
        with pytest.raises(ValueError, match="Cookie string is empty"):
            parse_cookie_string("")

    def test_whitespace_only_string(self) -> None:
        """Test that whitespace-only string raises ValueError."""
        with pytest.raises(ValueError, match="Cookie string is empty"):
            parse_cookie_string("   ")

    def test_no_valid_cookies(self) -> None:
        """Test that string with no valid cookies raises ValueError."""
        with pytest.raises(ValueError, match="No valid cookies found"):
            parse_cookie_string("invalid_cookie_without_equals")

    def test_skips_malformed_cookies(self) -> None:
        """Test that malformed cookies without equals are skipped."""
        result = parse_cookie_string("JSESSIONID=abc123; malformed; token=xyz")
        assert result == {"JSESSIONID": "abc123", "token": "xyz"}

    def test_empty_name_skipped(self) -> None:
        """Test that cookies with empty names are skipped."""
        result = parse_cookie_string("JSESSIONID=abc123; =value; token=xyz")
        assert result == {"JSESSIONID": "abc123", "token": "xyz"}

    def test_cookie_with_semicolon_in_value(self) -> None:
        """Test handling of semicolons - they split the string."""
        # Note: semicolons in values are not standard and will be split
        result = parse_cookie_string("JSESSIONID=abc;123")
        assert result == {"JSESSIONID": "abc"}  # Only first part is captured


class TestParseCookieFile:
    """Test cases for parse_cookie_file function."""

    def test_valid_netscape_format(self, tmp_path: Path) -> None:
        """Test parsing a valid Netscape-format cookie file."""
        cookie_file = tmp_path / "cookies.txt"
        cookie_file.write_text(
            "# Netscape HTTP Cookie File\n"
            ".example.com\tTRUE\t/\tFALSE\t0\tJSESSIONID\tabc123\n"
            ".example.com\tTRUE\t/\tTRUE\t0\ttoken\txyz789\n"
        )

        result = parse_cookie_file(cookie_file)
        assert result == {"JSESSIONID": "abc123", "token": "xyz789"}

    def test_file_with_comments_and_empty_lines(self, tmp_path: Path) -> None:
        """Test that comments and empty lines are skipped."""
        cookie_file = tmp_path / "cookies.txt"
        cookie_file.write_text(
            "# This is a comment\n"
            "\n"
            ".example.com\tTRUE\t/\tFALSE\t0\tJSESSIONID\tabc123\n"
            "# Another comment\n"
            "\n"
            ".example.com\tTRUE\t/\tFALSE\t0\ttoken\txyz\n"
        )

        result = parse_cookie_file(cookie_file)
        assert result == {"JSESSIONID": "abc123", "token": "xyz"}

    def test_duplicate_cookies_last_wins(self, tmp_path: Path) -> None:
        """Test that duplicate cookie names use the last value."""
        cookie_file = tmp_path / "cookies.txt"
        cookie_file.write_text(
            ".example.com\tTRUE\t/\tFALSE\t0\tJSESSIONID\tfirst\n"
            ".example.com\tTRUE\t/\tFALSE\t0\tJSESSIONID\tsecond\n"
        )

        result = parse_cookie_file(cookie_file)
        assert result == {"JSESSIONID": "second"}

    def test_file_not_found(self) -> None:
        """Test that non-existent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="Cookie file not found"):
            parse_cookie_file("/nonexistent/path/cookies.txt")

    def test_empty_file(self, tmp_path: Path) -> None:
        """Test that empty file raises ValueError."""
        cookie_file = tmp_path / "cookies.txt"
        cookie_file.write_text("")

        with pytest.raises(ValueError, match="No valid cookies found"):
            parse_cookie_file(cookie_file)

    def test_file_only_comments(self, tmp_path: Path) -> None:
        """Test that file with only comments raises ValueError."""
        cookie_file = tmp_path / "cookies.txt"
        cookie_file.write_text("# This is a comment\n# Another comment\n")

        with pytest.raises(ValueError, match="No valid cookies found"):
            parse_cookie_file(cookie_file)

    def test_malformed_lines_ignored(self, tmp_path: Path) -> None:
        """Test that lines with fewer than 7 fields are ignored."""
        cookie_file = tmp_path / "cookies.txt"
        cookie_file.write_text(
            ".example.com\tTRUE\t/\tFALSE\t0\tJSESSIONID\tabc123\n"
            "malformed line\n"
            ".example.com\tTRUE\t/\tFALSE\t0\ttoken\txyz\n"
        )

        result = parse_cookie_file(cookie_file)
        assert result == {"JSESSIONID": "abc123", "token": "xyz"}

    def test_path_parameter(self, tmp_path: Path) -> None:
        """Test that the function accepts both str and Path for file_path."""
        cookie_file = tmp_path / "cookies.txt"
        cookie_file.write_text(
            ".example.com\tTRUE\t/\tFALSE\t0\tJSESSIONID\tabc123\n"
        )

        # Test with Path object
        result_path = parse_cookie_file(cookie_file)
        assert result_path == {"JSESSIONID": "abc123"}

        # Test with string
        result_str = parse_cookie_file(str(cookie_file))
        assert result_str == {"JSESSIONID": "abc123"}


class TestResolveCookies:
    """Test cases for resolve_cookies function."""

    def test_cookie_string_only(self) -> None:
        """Test resolving cookies from a cookie string."""
        result = resolve_cookies(SecretStr("JSESSIONID=abc123"), "")
        assert result == {"JSESSIONID": "abc123"}

    def test_cookie_file_only(self, tmp_path: Path) -> None:
        """Test resolving cookies from a cookie file."""
        cookie_file = tmp_path / "cookies.txt"
        cookie_file.write_text(
            ".example.com\tTRUE\t/\tFALSE\t0\tJSESSIONID\tabc123\n"
        )

        result = resolve_cookies(None, str(cookie_file))
        assert result == {"JSESSIONID": "abc123"}

    def test_cookie_string_takes_precedence(self, tmp_path: Path) -> None:
        """Test that cookie string takes precedence over cookie file."""
        cookie_file = tmp_path / "cookies.txt"
        cookie_file.write_text(
            ".example.com\tTRUE\t/\tFALSE\t0\tJSESSIONID\tfrom_file\n"
        )

        result = resolve_cookies(SecretStr("JSESSIONID=from_string"), str(cookie_file))
        assert result == {"JSESSIONID": "from_string"}

    def test_empty_cookie_string_falls_back_to_file(self, tmp_path: Path) -> None:
        """Test that empty cookie string falls back to cookie file."""
        cookie_file = tmp_path / "cookies.txt"
        cookie_file.write_text(
            ".example.com\tTRUE\t/\tFALSE\t0\tJSESSIONID\tfrom_file\n"
        )

        result = resolve_cookies(SecretStr(""), str(cookie_file))
        assert result == {"JSESSIONID": "from_file"}

    def test_none_cookie_string_with_file(self, tmp_path: Path) -> None:
        """Test that None cookie string uses cookie file."""
        cookie_file = tmp_path / "cookies.txt"
        cookie_file.write_text(
            ".example.com\tTRUE\t/\tFALSE\t0\tJSESSIONID\tabc123\n"
        )

        result = resolve_cookies(None, str(cookie_file))
        assert result == {"JSESSIONID": "abc123"}

    def test_both_empty_returns_none(self) -> None:
        """Test that empty inputs return None."""
        result = resolve_cookies(SecretStr(""), "")
        assert result is None

    def test_both_none_returns_none(self) -> None:
        """Test that None inputs return None."""
        result = resolve_cookies(None, "")
        assert result is None

    def test_whitespace_cookie_string_treated_as_empty(self, tmp_path: Path) -> None:
        """Test that whitespace-only cookie string falls back to file."""
        cookie_file = tmp_path / "cookies.txt"
        cookie_file.write_text(
            ".example.com\tTRUE\t/\tFALSE\t0\tJSESSIONID\tfrom_file\n"
        )

        result = resolve_cookies(SecretStr("   "), str(cookie_file))
        assert result == {"JSESSIONID": "from_file"}

    def test_whitespace_cookie_file_treated_as_empty(self) -> None:
        """Test that whitespace-only cookie file path is treated as empty."""
        result = resolve_cookies(None, "   ")
        assert result is None