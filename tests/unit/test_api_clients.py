"""Unit tests for api_clients module."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
import requests
from atlassian.errors import ApiError
from pydantic import SecretStr

from confluence_markdown_exporter.api_clients import ApiClientFactory
from confluence_markdown_exporter.api_clients import get_confluence_instance
from confluence_markdown_exporter.api_clients import get_jira_instance
from confluence_markdown_exporter.api_clients import response_hook
from confluence_markdown_exporter.utils.app_data_store import ApiDetails
from confluence_markdown_exporter.utils.app_data_store import ConfigModel


class TestResponseHook:
    """Test cases for response_hook function."""

    def test_successful_response(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test that successful responses don't log warnings."""
        response = MagicMock(spec=requests.Response)
        response.ok = True
        response.status_code = 200

        result = response_hook(response)

        assert result == response
        assert len(caplog.records) == 0

    def test_failed_response(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test that failed responses log warnings."""
        response = MagicMock(spec=requests.Response)
        response.ok = False
        response.status_code = 404
        response.url = "https://test.atlassian.net/api/test"
        response.headers = {"Content-Type": "application/json"}

        result = response_hook(response)

        assert result == response
        assert len(caplog.records) == 1
        log_record = caplog.records[0]
        expected_msg = "Request to https://test.atlassian.net/api/test failed with status 404"
        assert expected_msg in log_record.message
        assert "Response headers: {'Content-Type': 'application/json'}" in log_record.message


class TestApiClientFactory:
    """Test cases for ApiClientFactory class."""

    def test_init(self) -> None:
        """Test ApiClientFactory initialization."""
        config = {"timeout": 30, "verify": True}
        factory = ApiClientFactory(config)
        assert factory.connection_config == config

    @patch("confluence_markdown_exporter.api_clients.ConfluenceApiSdk")
    def test_create_confluence_success(
        self, mock_confluence_sdk: MagicMock, sample_api_details: ApiDetails
    ) -> None:
        """Test successful Confluence client creation."""
        mock_instance = MagicMock()
        mock_instance.get_all_spaces.return_value = [{"key": "TEST"}]
        mock_confluence_sdk.return_value = mock_instance

        config = {"timeout": 30}
        factory = ApiClientFactory(config)

        result = factory.create_confluence(sample_api_details)

        assert result == mock_instance
        # With the new auth priority, PAT takes precedence over username/api_token
        mock_confluence_sdk.assert_called_once_with(
            url=str(sample_api_details.url),
            token=sample_api_details.pat.get_secret_value(),
            timeout=30,
        )
        mock_instance.get_all_spaces.assert_called_once_with(limit=1)

    @patch("confluence_markdown_exporter.api_clients.ConfluenceApiSdk")
    def test_create_confluence_connection_failure(
        self, mock_confluence_sdk: MagicMock, sample_api_details: ApiDetails
    ) -> None:
        """Test Confluence client creation with connection failure."""
        mock_instance = MagicMock()
        mock_instance.get_all_spaces.side_effect = ApiError("Connection failed")
        mock_confluence_sdk.return_value = mock_instance

        config = {"timeout": 30}
        factory = ApiClientFactory(config)

        with pytest.raises(ConnectionError, match="Confluence connection failed"):
            factory.create_confluence(sample_api_details)

    @patch("confluence_markdown_exporter.api_clients.JiraApiSdk")
    def test_create_jira_success(
        self, mock_jira_sdk: MagicMock, sample_api_details: ApiDetails
    ) -> None:
        """Test successful Jira client creation."""
        mock_instance = MagicMock()
        mock_instance.get_all_projects.return_value = [{"key": "TEST"}]
        mock_jira_sdk.return_value = mock_instance

        config = {"timeout": 30}
        factory = ApiClientFactory(config)

        result = factory.create_jira(sample_api_details)

        assert result == mock_instance
        # With the new auth priority, PAT takes precedence over username/api_token
        mock_jira_sdk.assert_called_once_with(
            url=str(sample_api_details.url),
            token=sample_api_details.pat.get_secret_value(),
            timeout=30,
        )
        mock_instance.get_all_projects.assert_called_once()

    @patch("confluence_markdown_exporter.api_clients.JiraApiSdk")
    def test_create_jira_connection_failure(
        self, mock_jira_sdk: MagicMock, sample_api_details: ApiDetails
    ) -> None:
        """Test Jira client creation with connection failure."""
        mock_instance = MagicMock()
        mock_instance.get_all_projects.side_effect = ApiError("Connection failed")
        mock_jira_sdk.return_value = mock_instance

        config = {"timeout": 30}
        factory = ApiClientFactory(config)

        with pytest.raises(ConnectionError, match="Jira connection failed"):
            factory.create_jira(sample_api_details)


class TestGetConfluenceInstance:
    """Test cases for get_confluence_instance function."""

    @patch("confluence_markdown_exporter.api_clients.get_settings")
    @patch("confluence_markdown_exporter.api_clients.ApiClientFactory")
    def test_successful_connection(
        self,
        mock_factory_class: MagicMock,
        mock_get_settings: MagicMock,
        sample_config_model: ConfigModel,
    ) -> None:
        """Test successful Confluence instance creation."""
        mock_get_settings.return_value = sample_config_model
        mock_factory = MagicMock()
        mock_confluence = MagicMock()
        mock_factory.create_confluence.return_value = mock_confluence
        mock_factory_class.return_value = mock_factory

        result = get_confluence_instance()

        assert result == mock_confluence
        mock_factory_class.assert_called_once_with(
            sample_config_model.connection_config.model_dump(exclude={"use_v2_api"})
        )
        mock_factory.create_confluence.assert_called_once_with(sample_config_model.auth.confluence)

    @patch("confluence_markdown_exporter.api_clients.get_settings")
    @patch("confluence_markdown_exporter.api_clients.ApiClientFactory")
    @patch("confluence_markdown_exporter.api_clients.main_config_menu_loop")
    @patch("confluence_markdown_exporter.api_clients.questionary.print")
    def test_connection_failure_retry(
        self,
        mock_questionary_print: MagicMock,
        mock_config_menu: MagicMock,
        mock_factory_class: MagicMock,
        mock_get_settings: MagicMock,
        sample_config_model: ConfigModel,
    ) -> None:
        """Test Confluence connection failure and retry."""
        # First call returns original config, second call returns updated config
        mock_get_settings.side_effect = [sample_config_model, sample_config_model]

        mock_factory = MagicMock()
        mock_confluence = MagicMock()
        # First attempt fails, second attempt succeeds
        mock_factory.create_confluence.side_effect = [
            ConnectionError("Connection failed"),
            mock_confluence,
        ]
        mock_factory_class.return_value = mock_factory

        result = get_confluence_instance()

        assert result == mock_confluence
        assert mock_factory.create_confluence.call_count == 2
        mock_questionary_print.assert_called_once()
        mock_config_menu.assert_called_once_with("auth.confluence")


class TestGetJiraInstance:
    """Test cases for get_jira_instance function."""

    @patch("confluence_markdown_exporter.api_clients.get_settings")
    @patch("confluence_markdown_exporter.api_clients.ApiClientFactory")
    def test_successful_connection(
        self,
        mock_factory_class: MagicMock,
        mock_get_settings: MagicMock,
        sample_config_model: ConfigModel,
    ) -> None:
        """Test successful Jira instance creation."""
        mock_get_settings.return_value = sample_config_model
        mock_factory = MagicMock()
        mock_jira = MagicMock()
        mock_factory.create_jira.return_value = mock_jira
        mock_factory_class.return_value = mock_factory

        # Clear cache to ensure fresh call
        get_jira_instance.cache_clear()

        result = get_jira_instance()

        assert result == mock_jira
        mock_factory_class.assert_called_once_with(
            sample_config_model.connection_config.model_dump(exclude={"use_v2_api"})
        )
        mock_factory.create_jira.assert_called_once_with(sample_config_model.auth.jira)

    @patch("confluence_markdown_exporter.api_clients.get_settings")
    @patch("confluence_markdown_exporter.api_clients.ApiClientFactory")
    def test_caching_behavior(
        self,
        mock_factory_class: MagicMock,
        mock_get_settings: MagicMock,
        sample_config_model: ConfigModel,
    ) -> None:
        """Test that Jira instance is cached."""
        mock_get_settings.return_value = sample_config_model
        mock_factory = MagicMock()
        mock_jira = MagicMock()
        mock_factory.create_jira.return_value = mock_jira
        mock_factory_class.return_value = mock_factory

        # Clear cache to ensure fresh start
        get_jira_instance.cache_clear()

        # First call
        result1 = get_jira_instance()
        # Second call
        result2 = get_jira_instance()

        assert result1 == result2 == mock_jira
        # Factory should only be called once due to caching
        assert mock_factory_class.call_count == 1
        assert mock_factory.create_jira.call_count == 1


class TestGetAuthParams:
    """Test cases for ApiClientFactory._get_auth_params method."""

    def test_cookie_string_auth(self) -> None:
        """Test authentication with cookie string."""
        auth = ApiDetails(
            url="https://test.atlassian.net/",
            cookies=SecretStr("JSESSIONID=abc123; token=xyz"),
        )
        factory = ApiClientFactory({})

        result = factory._get_auth_params(auth)

        assert result == {"cookies": {"JSESSIONID": "abc123", "token": "xyz"}}

    def test_cookie_file_auth(self, tmp_path: Path) -> None:
        """Test authentication with cookie file."""
        cookie_file = tmp_path / "cookies.txt"
        cookie_file.write_text(
            ".example.com\tTRUE\t/\tFALSE\t0\tJSESSIONID\tabc123\n"
        )

        auth = ApiDetails(
            url="https://test.atlassian.net/",
            cookie_file=str(cookie_file),
        )
        factory = ApiClientFactory({})

        result = factory._get_auth_params(auth)

        assert result == {"cookies": {"JSESSIONID": "abc123"}}

    def test_cookie_string_takes_precedence_over_pat(self) -> None:
        """Test that cookie string takes precedence over PAT."""
        auth = ApiDetails(
            url="https://test.atlassian.net/",
            cookies=SecretStr("JSESSIONID=abc123"),
            pat=SecretStr("my-pat-token"),
        )
        factory = ApiClientFactory({})

        result = factory._get_auth_params(auth)

        assert result == {"cookies": {"JSESSIONID": "abc123"}}

    def test_cookie_string_takes_precedence_over_basic_auth(self) -> None:
        """Test that cookie string takes precedence over basic auth."""
        auth = ApiDetails(
            url="https://test.atlassian.net/",
            cookies=SecretStr("JSESSIONID=abc123"),
            username=SecretStr("user@example.com"),
            api_token=SecretStr("api-token"),
        )
        factory = ApiClientFactory({})

        result = factory._get_auth_params(auth)

        assert result == {"cookies": {"JSESSIONID": "abc123"}}

    def test_cookie_file_takes_precedence_over_pat(self, tmp_path: Path) -> None:
        """Test that cookie file takes precedence over PAT."""
        cookie_file = tmp_path / "cookies.txt"
        cookie_file.write_text(
            ".example.com\tTRUE\t/\tFALSE\t0\tJSESSIONID\tabc123\n"
        )

        auth = ApiDetails(
            url="https://test.atlassian.net/",
            cookie_file=str(cookie_file),
            pat=SecretStr("my-pat-token"),
        )
        factory = ApiClientFactory({})

        result = factory._get_auth_params(auth)

        assert result == {"cookies": {"JSESSIONID": "abc123"}}

    def test_pat_auth(self) -> None:
        """Test authentication with PAT."""
        auth = ApiDetails(
            url="https://test.atlassian.net/",
            pat=SecretStr("my-pat-token"),
        )
        factory = ApiClientFactory({})

        result = factory._get_auth_params(auth)

        assert result == {"token": "my-pat-token"}

    def test_pat_takes_precedence_over_basic_auth(self) -> None:
        """Test that PAT takes precedence over basic auth."""
        auth = ApiDetails(
            url="https://test.atlassian.net/",
            pat=SecretStr("my-pat-token"),
            username=SecretStr("user@example.com"),
            api_token=SecretStr("api-token"),
        )
        factory = ApiClientFactory({})

        result = factory._get_auth_params(auth)

        assert result == {"token": "my-pat-token"}

    def test_basic_auth(self) -> None:
        """Test authentication with username and API token."""
        auth = ApiDetails(
            url="https://test.atlassian.net/",
            username=SecretStr("user@example.com"),
            api_token=SecretStr("api-token"),
        )
        factory = ApiClientFactory({})

        result = factory._get_auth_params(auth)

        assert result == {"username": "user@example.com", "password": "api-token"}

    def test_no_auth_returns_empty_dict(self) -> None:
        """Test that missing auth returns empty dict."""
        auth = ApiDetails(url="https://test.atlassian.net/")
        factory = ApiClientFactory({})

        result = factory._get_auth_params(auth)

        assert result == {}


class TestApiClientFactoryWithCookies:
    """Test cases for ApiClientFactory with cookie authentication."""

    @patch("confluence_markdown_exporter.api_clients.ConfluenceApiSdk")
    def test_create_confluence_with_cookie_string(
        self, mock_confluence_sdk: MagicMock
    ) -> None:
        """Test Confluence client creation with cookie string."""
        mock_instance = MagicMock()
        mock_instance.get_all_spaces.return_value = [{"key": "TEST"}]
        mock_confluence_sdk.return_value = mock_instance

        auth = ApiDetails(
            url="https://test.atlassian.net/",
            cookies=SecretStr("JSESSIONID=abc123"),
        )
        config = {"timeout": 30}
        factory = ApiClientFactory(config)

        result = factory.create_confluence(auth)

        assert result == mock_instance
        mock_confluence_sdk.assert_called_once_with(
            url="https://test.atlassian.net/",
            cookies={"JSESSIONID": "abc123"},
            timeout=30,
        )

    @patch("confluence_markdown_exporter.api_clients.JiraApiSdk")
    def test_create_jira_with_cookie_string(
        self, mock_jira_sdk: MagicMock
    ) -> None:
        """Test Jira client creation with cookie string."""
        mock_instance = MagicMock()
        mock_instance.get_all_projects.return_value = [{"key": "TEST"}]
        mock_jira_sdk.return_value = mock_instance

        auth = ApiDetails(
            url="https://test.atlassian.net/",
            cookies=SecretStr("JSESSIONID=abc123"),
        )
        config = {"timeout": 30}
        factory = ApiClientFactory(config)

        result = factory.create_jira(auth)

        assert result == mock_instance
        mock_jira_sdk.assert_called_once_with(
            url="https://test.atlassian.net/",
            cookies={"JSESSIONID": "abc123"},
            timeout=30,
        )

    @patch("confluence_markdown_exporter.api_clients.ConfluenceApiSdk")
    def test_create_confluence_with_cookie_file(
        self, mock_confluence_sdk: MagicMock, tmp_path: Path
    ) -> None:
        """Test Confluence client creation with cookie file."""
        cookie_file = tmp_path / "cookies.txt"
        cookie_file.write_text(
            ".example.com\tTRUE\t/\tFALSE\t0\tJSESSIONID\tabc123\n"
        )

        mock_instance = MagicMock()
        mock_instance.get_all_spaces.return_value = [{"key": "TEST"}]
        mock_confluence_sdk.return_value = mock_instance

        auth = ApiDetails(
            url="https://test.atlassian.net/",
            cookie_file=str(cookie_file),
        )
        config = {"timeout": 30}
        factory = ApiClientFactory(config)

        result = factory.create_confluence(auth)

        assert result == mock_instance
        mock_confluence_sdk.assert_called_once_with(
            url="https://test.atlassian.net/",
            cookies={"JSESSIONID": "abc123"},
            timeout=30,
        )
