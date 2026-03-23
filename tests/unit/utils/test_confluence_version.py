"""Unit tests for Confluence version detection module."""

import pytest
from unittest.mock import MagicMock
from unittest.mock import patch

from confluence_markdown_exporter.utils.confluence_version import (
    ConfluenceServerInfo,
    _detect_cloud_from_url,
    _parse_version,
    clear_confluence_server_info,
    get_confluence_server_info,
    set_confluence_server_info,
    should_use_v2_api,
)


class TestConfluenceServerInfo:
    """Test cases for ConfluenceServerInfo dataclass."""

    def test_server_info_properties(self) -> None:
        """Test server info property methods."""
        info = ConfluenceServerInfo(
            version="7.4.11",
            build_number=74011,
            deployment_type="server",
        )

        assert info.is_server is True
        assert info.is_cloud is False
        assert info.is_data_center is False

    def test_cloud_info_properties(self) -> None:
        """Test cloud instance properties."""
        info = ConfluenceServerInfo(
            version="cloud",
            build_number=0,
            deployment_type="cloud",
        )

        assert info.is_cloud is True
        assert info.is_server is False
        assert info.is_data_center is False

    def test_data_center_info_properties(self) -> None:
        """Test data center instance properties."""
        info = ConfluenceServerInfo(
            version="8.5.20",
            build_number=8520,
            deployment_type="data_center",
        )

        assert info.is_data_center is True
        assert info.is_server is False
        assert info.is_cloud is False

    def test_supports_v2_api_cloud(self) -> None:
        """Cloud instances always support v2 API."""
        info = ConfluenceServerInfo(
            version="cloud",
            build_number=0,
            deployment_type="cloud",
        )
        assert info.supports_v2_api is True

    def test_supports_v2_api_server(self) -> None:
        """Server instances never support v2 API."""
        info = ConfluenceServerInfo(
            version="8.5.20",
            build_number=8520,
            deployment_type="server",
        )
        assert info.supports_v2_api is False

    def test_supports_v2_api_data_center_8_plus(self) -> None:
        """Data Center 8+ supports v2 API."""
        info = ConfluenceServerInfo(
            version="8.0.0",
            build_number=8000,
            deployment_type="data_center",
        )
        assert info.supports_v2_api is True

        info = ConfluenceServerInfo(
            version="8.5.20",
            build_number=8520,
            deployment_type="data_center",
        )
        assert info.supports_v2_api is True

    def test_supports_v2_api_data_center_7(self) -> None:
        """Data Center 7.x does not support v2 API."""
        info = ConfluenceServerInfo(
            version="7.4.11",
            build_number=74011,
            deployment_type="data_center",
        )
        assert info.supports_v2_api is False

    def test_supports_v2_api_data_center_edge_case(self) -> None:
        """Data Center exactly 8.0.0 supports v2 API."""
        info = ConfluenceServerInfo(
            version="8.0.0",
            build_number=8000,
            deployment_type="data_center",
        )
        assert info.supports_v2_api is True


class TestParseVersion:
    """Test cases for version parsing."""

    def test_parse_simple_version(self) -> None:
        """Parse simple version strings."""
        assert _parse_version("7.4.11") == (7, 4, 11)
        assert _parse_version("8.5.20") == (8, 5, 20)
        assert _parse_version("8.0.0") == (8, 0, 0)

    def test_parse_two_part_version(self) -> None:
        """Parse two-part version strings."""
        assert _parse_version("8.0") == (8, 0)
        assert _parse_version("7.4") == (7, 4)

    def test_parse_single_part_version(self) -> None:
        """Parse single-part version strings."""
        assert _parse_version("8") == (8,)

    def test_parse_version_with_suffix(self) -> None:
        """Parse version strings with suffixes like -SNAPSHOT."""
        assert _parse_version("7.4.11-SNAPSHOT") == (7, 4, 11)
        assert _parse_version("8.5.20-rc1") == (8, 5, 20)

    def test_parse_version_with_whitespace(self) -> None:
        """Parse version strings with leading/trailing whitespace."""
        assert _parse_version("  7.4.11  ") == (7, 4, 11)

    def test_parse_version_invalid(self) -> None:
        """Invalid version strings raise ValueError."""
        with pytest.raises(ValueError):
            _parse_version("invalid")
        with pytest.raises(ValueError):
            _parse_version("")


class TestVersionGte:
    """Test cases for version comparison."""

    def test_version_gte_equal(self) -> None:
        """Test version equality."""
        info = ConfluenceServerInfo(
            version="8.0.0",
            build_number=8000,
            deployment_type="data_center",
        )
        assert info._version_gte("8.0.0") is True

    def test_version_gte_greater(self) -> None:
        """Test version greater than target."""
        info = ConfluenceServerInfo(
            version="8.5.20",
            build_number=8520,
            deployment_type="data_center",
        )
        assert info._version_gte("8.0.0") is True

    def test_version_gte_less(self) -> None:
        """Test version less than target."""
        info = ConfluenceServerInfo(
            version="7.4.11",
            build_number=74011,
            deployment_type="data_center",
        )
        assert info._version_gte("8.0.0") is False


class TestDetectCloudFromUrl:
    """Test cases for Cloud URL detection."""

    def test_atlassian_net_is_cloud(self) -> None:
        """atlassian.net URLs are Cloud instances."""
        assert _detect_cloud_from_url("https://example.atlassian.net") is True
        assert _detect_cloud_from_url("https://company.atlassian.net/wiki") is True

    def test_atlassian_com_is_cloud(self) -> None:
        """atlassian.com URLs are Cloud instances."""
        assert _detect_cloud_from_url("https://example.atlassian.com") is True

    def test_self_hosted_is_not_cloud(self) -> None:
        """Self-hosted URLs are not Cloud instances."""
        assert _detect_cloud_from_url("https://confluence.company.com") is False
        assert _detect_cloud_from_url("https://wiki.internal.org") is False

    def test_localhost_is_not_cloud(self) -> None:
        """localhost URLs are not Cloud instances."""
        assert _detect_cloud_from_url("http://localhost:8090") is False


class TestShouldUseV2Api:
    """Test cases for should_use_v2_api function."""

    def setup_method(self) -> None:
        """Clear cached server info before each test."""
        clear_confluence_server_info()

    def teardown_method(self) -> None:
        """Clear cached server info after each test."""
        clear_confluence_server_info()

    def test_explicit_true(self) -> None:
        """Explicit True returns True."""
        assert should_use_v2_api(True) is True

    def test_explicit_false(self) -> None:
        """Explicit False returns False."""
        assert should_use_v2_api(False) is False

    def test_string_true(self) -> None:
        """String 'true' returns True."""
        assert should_use_v2_api("true") is True
        assert should_use_v2_api("TRUE") is True
        assert should_use_v2_api("True") is True

    def test_string_false(self) -> None:
        """String 'false' returns False."""
        assert should_use_v2_api("false") is False
        assert should_use_v2_api("FALSE") is False
        assert should_use_v2_api("False") is False

    def test_auto_with_cloud_server(self) -> None:
        """Auto with Cloud instance returns True."""
        set_confluence_server_info(
            ConfluenceServerInfo(
                version="cloud",
                build_number=0,
                deployment_type="cloud",
            )
        )
        assert should_use_v2_api("auto") is True

    def test_auto_with_data_center_8_plus(self) -> None:
        """Auto with Data Center 8+ returns True."""
        set_confluence_server_info(
            ConfluenceServerInfo(
                version="8.5.20",
                build_number=8520,
                deployment_type="data_center",
            )
        )
        assert should_use_v2_api("auto") is True

    def test_auto_with_data_center_7(self) -> None:
        """Auto with Data Center 7.x returns False."""
        set_confluence_server_info(
            ConfluenceServerInfo(
                version="7.4.11",
                build_number=74011,
                deployment_type="data_center",
            )
        )
        assert should_use_v2_api("auto") is False

    def test_auto_with_server(self) -> None:
        """Auto with Server instance returns False."""
        set_confluence_server_info(
            ConfluenceServerInfo(
                version="7.4.11",
                build_number=74011,
                deployment_type="server",
            )
        )
        assert should_use_v2_api("auto") is False

    def test_auto_without_server_info(self) -> None:
        """Auto without server info returns False (conservative)."""
        clear_confluence_server_info()
        assert should_use_v2_api("auto") is False

    def test_unknown_string_defaults_to_auto(self) -> None:
        """Unknown string value defaults to auto behavior."""
        set_confluence_server_info(
            ConfluenceServerInfo(
                version="8.5.20",
                build_number=8520,
                deployment_type="data_center",
            )
        )
        # Unknown string should be treated as auto
        assert should_use_v2_api("unknown") is True


class TestGetConfluenceServerInfo:
    """Test cases for get_confluence_server_info function."""

    def setup_method(self) -> None:
        """Clear cached server info before each test."""
        clear_confluence_server_info()

    def teardown_method(self) -> None:
        """Clear cached server info after each test."""
        clear_confluence_server_info()

    def test_returns_cached_info(self) -> None:
        """Returns cached server info without detection."""
        cached_info = ConfluenceServerInfo(
            version="8.5.20",
            build_number=8520,
            deployment_type="data_center",
        )
        set_confluence_server_info(cached_info)

        result = get_confluence_server_info()
        assert result == cached_info

    def test_returns_none_without_confluence_client(self) -> None:
        """Returns None if no client provided and no cached info."""
        result = get_confluence_server_info()
        assert result is None

    def test_detects_from_systeminfo(self) -> None:
        """Detects version from systeminfo endpoint."""
        mock_confluence = MagicMock()
        mock_confluence.url = "https://confluence.example.com"
        mock_confluence.get.return_value = {
            "version": "7.4.11",
            "buildNumber": 74011,
        }

        result = get_confluence_server_info(mock_confluence)

        assert result is not None
        assert result.version == "7.4.11"
        assert result.build_number == 74011
        assert result.deployment_type == "server"
        mock_confluence.get.assert_called_once_with("rest/applinks/latest/systeminfo")

    def test_detects_data_center_from_response(self) -> None:
        """Detects Data Center from response fields."""
        mock_confluence = MagicMock()
        mock_confluence.url = "https://confluence.example.com"
        mock_confluence.get.return_value = {
            "version": "8.5.20",
            "buildNumber": 8520,
            "dataCenter": True,
        }

        result = get_confluence_server_info(mock_confluence)

        assert result is not None
        assert result.deployment_type == "data_center"

    def test_detects_cloud_from_url(self) -> None:
        """Detects Cloud from URL pattern when systeminfo fails."""
        mock_confluence = MagicMock()
        mock_confluence.url = "https://company.atlassian.net"
        mock_confluence.get.side_effect = Exception("systeminfo not available")

        result = get_confluence_server_info(mock_confluence)

        assert result is not None
        assert result.deployment_type == "cloud"

    def test_detects_from_v2_probe(self) -> None:
        """Detects version from v2 API probe when other methods fail."""
        mock_confluence = MagicMock()
        mock_confluence.url = "https://confluence.example.com"
        # First call (systeminfo) fails, second call (v2 probe) succeeds
        mock_confluence.get.side_effect = [
            Exception("systeminfo not available"),
            {"results": []},  # v2 API response
        ]

        result = get_confluence_server_info(mock_confluence)

        assert result is not None
        assert result.deployment_type == "data_center"
        assert result.supports_v2_api is True

    def test_returns_none_on_all_failures(self) -> None:
        """Returns None when all detection methods fail."""
        mock_confluence = MagicMock()
        mock_confluence.url = "https://confluence.example.com"
        mock_confluence.get.side_effect = Exception("all API calls fail")

        result = get_confluence_server_info(mock_confluence)

        assert result is None