"""Cookie parsing utilities for authentication.

This module provides functions to parse cookies from strings and Netscape-format
cookie files for use with Confluence/Jira authentication.
"""

from __future__ import annotations

import re
from pathlib import Path

from pydantic import SecretStr


def parse_cookie_string(cookie_string: str) -> dict[str, str]:
    """Parse a cookie string into a dictionary.

    Args:
        cookie_string: A cookie string in the format "name1=value1; name2=value2".

    Returns:
        A dictionary mapping cookie names to values.

    Raises:
        ValueError: If the cookie string is empty or contains no valid cookies.

    Examples:
        >>> parse_cookie_string("JSESSIONID=abc123")
        {'JSESSIONID': 'abc123'}
        >>> parse_cookie_string("JSESSIONID=abc123; token=xyz")
        {'JSESSIONID': 'abc123', 'token': 'xyz'}
    """
    if not cookie_string or not cookie_string.strip():
        msg = "Cookie string is empty"
        raise ValueError(msg)

    cookies: dict[str, str] = {}
    # Split by semicolon, but be careful with values that might contain semicolons
    parts = cookie_string.split(";")

    for part in parts:
        part = part.strip()
        if not part:
            continue

        # Find the first equals sign to split name and value
        eq_pos = part.find("=")
        if eq_pos == -1:
            # Skip malformed cookies without equals sign
            continue

        name = part[:eq_pos].strip()
        value = part[eq_pos + 1 :].strip()

        if name:
            cookies[name] = value

    if not cookies:
        msg = "No valid cookies found in string"
        raise ValueError(msg)

    return cookies


def parse_cookie_file(file_path: str | Path) -> dict[str, str]:
    """Parse a Netscape-format cookie file into a dictionary.

    The Netscape cookie file format is tab-separated with the following columns:
    domain, flag, path, secure, expiry, name, value

    Args:
        file_path: Path to the cookie file.

    Returns:
        A dictionary mapping cookie names to values.

    Raises:
        FileNotFoundError: If the cookie file does not exist.
        ValueError: If the file contains no valid cookies.

    Examples:
        >>> parse_cookie_file("/path/to/cookies.txt")
        {'JSESSIONID': 'abc123', 'token': 'xyz'}
    """
    path = Path(file_path)

    if not path.exists():
        msg = f"Cookie file not found: {file_path}"
        raise FileNotFoundError(msg)

    cookies: dict[str, str] = []
    content = path.read_text()

    for line in content.splitlines():
        line = line.strip()

        # Skip empty lines and comments
        if not line or line.startswith("#"):
            continue

        # Parse Netscape format: domain, flag, path, secure, expiry, name, value
        parts = line.split("\t")

        if len(parts) >= 7:
            name = parts[5]
            value = parts[6]
            if name:
                cookies.append((name, value))

    if not cookies:
        msg = f"No valid cookies found in file: {file_path}"
        raise ValueError(msg)

    # Convert list to dict (last occurrence wins for duplicate names)
    return dict(cookies)


def resolve_cookies(cookie_string: SecretStr | None, cookie_file: str) -> dict[str, str] | None:
    """Resolve cookies from either a cookie string or a cookie file.

    If both are provided, the cookie string takes precedence.

    Args:
        cookie_string: A SecretStr containing the cookie string.
        cookie_file: Path to a Netscape-format cookie file.

    Returns:
        A dictionary mapping cookie names to values, or None if neither is provided.

    Raises:
        ValueError: If the cookie string or file is invalid.
        FileNotFoundError: If the cookie file does not exist.

    Examples:
        >>> resolve_cookies(SecretStr("JSESSIONID=abc123"), "")
        {'JSESSIONID': 'abc123'}
        >>> resolve_cookies(None, "/path/to/cookies.txt")
        {'JSESSIONID': 'abc123'}
    """
    # Check cookie string first (takes precedence)
    if cookie_string:
        cookie_value = cookie_string.get_secret_value()
        if cookie_value and cookie_value.strip():
            return parse_cookie_string(cookie_value)

    # Fall back to cookie file
    if cookie_file and cookie_file.strip():
        return parse_cookie_file(cookie_file)

    return None