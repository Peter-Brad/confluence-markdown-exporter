from __future__ import annotations

import logging
import os
from functools import lru_cache
from typing import Any

import questionary
import requests
from atlassian import Confluence as ConfluenceApiSdk
from atlassian import Jira as JiraApiSdk
from questionary import Style

from confluence_markdown_exporter.utils.app_data_store import ApiDetails
from confluence_markdown_exporter.utils.app_data_store import get_settings
from confluence_markdown_exporter.utils.app_data_store import set_setting
from confluence_markdown_exporter.utils.config_interactive import main_config_menu_loop
from confluence_markdown_exporter.utils.confluence_version import get_confluence_server_info
from confluence_markdown_exporter.utils.cookie_parser import resolve_cookies
from confluence_markdown_exporter.utils.type_converter import str_to_bool

DEBUG: bool = str_to_bool(os.getenv("DEBUG", "False"))

logger = logging.getLogger(__name__)


def response_hook(
    response: requests.Response, *_args: object, **_kwargs: object
) -> requests.Response:
    """Log response headers when requests fail."""
    if not response.ok:
        logger.warning(
            f"Request to {response.url} failed with status {response.status_code}"
            f"Response headers: {dict(response.headers)}"
        )
    return response


class ApiClientFactory:
    """Factory for creating authenticated Confluence and Jira API clients with retry config."""

    def __init__(self, connection_config: dict[str, Any]) -> None:
        self.connection_config = connection_config

    def _get_auth_params(self, auth: ApiDetails) -> dict[str, Any]:
        """Build authentication parameters based on the priority order.

        Priority order:
        1. cookies string -> Cookie authentication
        2. cookie_file -> Parse and use cookie authentication
        3. PAT -> Bearer token authentication
        4. username + api_token -> Basic authentication

        Args:
            auth: The ApiDetails containing authentication credentials.

        Returns:
            A dictionary of authentication parameters for the API client.
        """
        # Try cookie authentication first
        cookies = resolve_cookies(auth.cookies, auth.cookie_file)
        if cookies:
            return {"cookies": cookies}

        # Try PAT authentication
        pat_value = auth.pat.get_secret_value()
        if pat_value:
            return {"token": pat_value}

        # Fall back to basic authentication
        username = auth.username.get_secret_value()
        api_token = auth.api_token.get_secret_value()
        if username and api_token:
            return {"username": username, "password": api_token}

        # No valid authentication found
        return {}

    def create_confluence(self, auth: ApiDetails) -> ConfluenceApiSdk:
        try:
            auth_params = self._get_auth_params(auth)
            instance = ConfluenceApiSdk(
                url=str(auth.url),
                **auth_params,
                **self.connection_config,
            )
            instance.get_all_spaces(limit=1)
        except Exception as e:
            msg = f"Confluence connection failed: {e}"
            raise ConnectionError(msg) from e

        # Detect and cache server version info
        server_info = get_confluence_server_info(instance)
        if server_info:
            logger.info(
                f"Connected to Confluence {server_info.deployment_type} {server_info.version}"
            )
        else:
            logger.info("Connected to Confluence (version detection failed)")

        return instance

    def create_jira(self, auth: ApiDetails) -> JiraApiSdk:
        try:
            auth_params = self._get_auth_params(auth)
            instance = JiraApiSdk(
                url=str(auth.url),
                **auth_params,
                **self.connection_config,
            )
            instance.get_all_projects()
        except Exception as e:
            msg = f"Jira connection failed: {e}"
            raise ConnectionError(msg) from e
        return instance


def get_confluence_instance() -> ConfluenceApiSdk:
    """Get authenticated Confluence API client using current settings."""
    settings = get_settings()
    auth = settings.auth
    connection_config = settings.connection_config.model_dump(exclude={"use_v2_api"})

    while True:
        try:
            confluence = ApiClientFactory(connection_config).create_confluence(auth.confluence)
            break
        except ConnectionError as e:
            questionary.print(
                f"{e}\nRedirecting to Confluence authentication config...",
                style="fg:red bold",
            )
            main_config_menu_loop("auth.confluence")
            settings = get_settings()
            auth = settings.auth

    if DEBUG:
        confluence.session.hooks["response"] = [response_hook]

    return confluence


@lru_cache(maxsize=1)
def get_jira_instance() -> JiraApiSdk:
    """Get authenticated Jira API client using current settings with required authentication."""
    settings = get_settings()
    auth = settings.auth
    connection_config = settings.connection_config.model_dump(exclude={"use_v2_api"})

    while True:
        try:
            jira = ApiClientFactory(connection_config).create_jira(auth.jira)
            break
        except ConnectionError:
            # Ask if user wants to use Confluence credentials for Jira
            use_confluence = questionary.confirm(
                "Jira connection failed. Use the same authentication as for Confluence?",
                default=False,
                style=Style([("question", "fg:yellow")]),
            ).ask()
            if use_confluence:
                set_setting("auth.jira", auth.confluence.model_dump())
                settings = get_settings()
                auth = settings.auth
                continue

            questionary.print(
                "Redirecting to Jira authentication config...",
                style="fg:red bold",
            )
            main_config_menu_loop("auth.jira")
            settings = get_settings()
            auth = settings.auth

    if DEBUG:
        jira.session.hooks["response"] = [response_hook]

    return jira
