"""Confluence version detection module.

Provides utilities for detecting Confluence server version and capabilities,
enabling automatic API version selection for compatibility across
Confluence Cloud, Data Center, and Server deployments.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import Literal
from urllib.parse import urlparse

if TYPE_CHECKING:
    from atlassian import Confluence

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ConfluenceServerInfo:
    """Information about a Confluence server instance.

    Attributes:
        version: The version string (e.g., "7.4.11", "8.5.20").
        build_number: The build number as an integer.
        deployment_type: The type of deployment ("cloud", "data_center", or "server").
    """

    version: str
    build_number: int
    deployment_type: Literal["cloud", "data_center", "server"]

    @property
    def is_cloud(self) -> bool:
        """Check if this is a Cloud instance."""
        return self.deployment_type == "cloud"

    @property
    def is_data_center(self) -> bool:
        """Check if this is a Data Center instance."""
        return self.deployment_type == "data_center"

    @property
    def is_server(self) -> bool:
        """Check if this is a Server instance."""
        return self.deployment_type == "server"

    @property
    def supports_v2_api(self) -> bool:
        """Check if this instance supports the v2 REST API.

        v2 API is available on:
        - Confluence Cloud (always)
        - Confluence Data Center 8.0.0+
        - NOT available on Confluence Server (self-hosted, non-DC)
        """
        if self.is_cloud:
            return True
        if self.is_server:
            return False
        # Data Center: check version >= 8.0.0
        return self._version_gte("8.0.0")

    def _version_gte(self, target: str) -> bool:
        """Check if version is greater than or equal to target."""
        try:
            return _parse_version(self.version) >= _parse_version(target)
        except (ValueError, TypeError):
            logger.warning(
                f"Could not parse version '{self.version}', assuming it does not support target '{target}'"
            )
            return False


def _parse_version(version_str: str) -> tuple[int, ...]:
    """Parse a version string into a tuple of integers.

    Args:
        version_str: Version string like "7.4.11" or "8.5.20".

    Returns:
        Tuple of integers like (7, 4, 11).

    Raises:
        ValueError: If the version string cannot be parsed.
    """
    # Extract numeric parts (handle versions like "7.4.11-SNAPSHOT")
    match = re.match(r"^(\d+(?:\.\d+)*)", version_str.strip())
    if not match:
        raise ValueError(f"Invalid version string: {version_str}")

    return tuple(int(part) for part in match.group(1).split("."))


def _detect_cloud_from_url(url: str) -> bool:
    """Detect if the URL points to a Cloud instance.

    Cloud instances typically have URLs like:
    - https://example.atlassian.net
    - https://example.atlassian.com
    """
    parsed = urlparse(url)
    hostname = parsed.hostname or ""
    return hostname.endswith(".atlassian.net") or hostname.endswith(".atlassian.com")


def _detect_confluence_version(confluence: "Confluence") -> ConfluenceServerInfo | None:
    """Detect Confluence server version via multiple API endpoints.

    Detection strategy:
    1. Try /rest/applinks/latest/systeminfo (Server/DC)
    2. Check URL for atlassian.net/.atlassian.com (Cloud)
    3. Probe v2 API endpoint

    Args:
        confluence: The authenticated Confluence API client.

    Returns:
        ConfluenceServerInfo if detection succeeds, None otherwise.
    """
    url = str(confluence.url)

    # Strategy 1: Try system info endpoint (Server/Data Center)
    try:
        response = confluence.get("rest/applinks/latest/systeminfo")
        if response and "version" in response:
            version = response.get("version", "")
            build_number = response.get("buildNumber", 0)

            # Detect deployment type
            # Data Center typically has "dataCenter" in the response or a different productId
            deployment_type: Literal["cloud", "data_center", "server"] = "server"
            if response.get("dataCenter") or "Data Center" in response.get("productDescription", ""):
                deployment_type = "data_center"

            logger.debug(f"Detected Confluence {deployment_type} version {version} via systeminfo")
            return ConfluenceServerInfo(
                version=version,
                build_number=build_number,
                deployment_type=deployment_type,
            )
    except Exception as e:
        logger.debug(f"Could not fetch system info: {e}")

    # Strategy 2: Check URL for Cloud
    if _detect_cloud_from_url(url):
        logger.debug("Detected Confluence Cloud from URL pattern")
        return ConfluenceServerInfo(
            version="cloud",  # Cloud version is managed by Atlassian
            build_number=0,
            deployment_type="cloud",
        )

    # Strategy 3: Probe v2 API to determine version capability
    try:
        # Try a lightweight v2 API call
        response = confluence.get("api/v2/spaces?limit=1")
        if response is not None:
            # v2 API exists, assume DC 8+ (we couldn't get exact version)
            logger.debug("v2 API probe succeeded, assuming Data Center 8+")
            return ConfluenceServerInfo(
                version="8.0.0",  # Minimum version with v2 API
                build_number=0,
                deployment_type="data_center",
            )
    except Exception as e:
        logger.debug(f"v2 API probe failed: {e}")

    # Could not determine version
    logger.warning(
        "Could not detect Confluence version. "
        "Defaulting to Server mode with v1 API only."
    )
    return None


# Cached server info (populated on first connection)
_server_info: ConfluenceServerInfo | None = None


def get_confluence_server_info(confluence: "Confluence | None" = None) -> ConfluenceServerInfo | None:
    """Get cached server info or detect it if not cached.

    Args:
        confluence: Optional Confluence client to use for detection.
                   If None, returns the cached value without detection.

    Returns:
        ConfluenceServerInfo if available, None otherwise.
    """
    global _server_info  # noqa: PLW0603

    if _server_info is not None:
        return _server_info

    if confluence is not None:
        _server_info = _detect_confluence_version(confluence)

    return _server_info


def set_confluence_server_info(info: ConfluenceServerInfo) -> None:
    """Set the cached server info.

    This is primarily used for testing purposes.
    """
    global _server_info  # noqa: PLW0603
    _server_info = info


def clear_confluence_server_info() -> None:
    """Clear the cached server info.

    This is primarily used for testing purposes.
    """
    global _server_info  # noqa: PLW0603
    _server_info = None


def should_use_v2_api(config_value: bool | str | None) -> bool:
    """Determine whether to use v2 API based on config and detected server capabilities.

    Args:
        config_value: The configured value for use_v2_api:
            - "auto": Auto-detect based on server version (default)
            - True: Force use of v2 API
            - False: Force disable v2 API

    Returns:
        True if v2 API should be used, False otherwise.
    """
    # Handle explicit True/False
    if config_value is True:
        return True
    if config_value is False:
        return False

    # Handle string values
    if isinstance(config_value, str):
        if config_value.lower() == "true":
            return True
        if config_value.lower() == "false":
            return False
        if config_value.lower() == "auto":
            # Fall through to auto-detection
            pass
        else:
            logger.warning(f"Unknown use_v2_api value '{config_value}', defaulting to auto")
            # Fall through to auto-detection

    # Auto-detect: check server capabilities
    server_info = get_confluence_server_info()
    if server_info is None:
        # Could not detect, be conservative and use v1
        logger.info("Confluence version unknown, defaulting to v1 API")
        return False

    result = server_info.supports_v2_api
    logger.info(
        f"Confluence {server_info.deployment_type} {server_info.version}: "
        f"v2 API {'enabled' if result else 'disabled'}"
    )
    return result