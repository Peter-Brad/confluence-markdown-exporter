from __future__ import annotations

import os
from pathlib import Path
from typing import List
from typing import Literal
from typing import Optional

from typing_extensions import Annotated

import typer

from confluence_markdown_exporter import __version__
from confluence_markdown_exporter.utils.app_data_store import get_settings
from confluence_markdown_exporter.utils.app_data_store import set_setting
from confluence_markdown_exporter.utils.config_interactive import main_config_menu_loop
from confluence_markdown_exporter.utils.lockfile import LockfileManager
from confluence_markdown_exporter.utils.measure_time import measure
from confluence_markdown_exporter.utils.platform_compat import handle_powershell_tilde_expansion
from confluence_markdown_exporter.utils.type_converter import str_to_bool

DEBUG: bool = str_to_bool(os.getenv("DEBUG", "False"))

app = typer.Typer()


def override_output_path_config(value: Optional[Path]) -> None:
    """Override the default output path if provided."""
    if value is not None:
        set_setting("export.output_path", value)


def override_export_format(value: Optional[str]) -> None:
    """Override the export format if provided."""
    if value is not None:
        set_setting("export.export_format", value)


@app.command(help="Export one or more Confluence pages by ID or URL.")
def pages(
    pages: Annotated[List[str], typer.Argument(help="Page ID(s) or URL(s)")],
    output_path: Annotated[
        Optional[Path],
        typer.Option(
            help="Directory to write exported files to. Overrides config if set."
        ),
    ] = None,
    format: Annotated[
        Optional[str],
        typer.Option(
            "--format",
            "-f",
            help="Output format: markdown, html, or both. Overrides config if set.",
        ),
    ] = None,
) -> None:
    from confluence_markdown_exporter.confluence import Page
    from confluence_markdown_exporter.confluence import sync_removed_pages

    with measure(f"Export pages {', '.join(pages)}"):
        override_output_path_config(output_path)
        override_export_format(format)
        LockfileManager.init()
        for page in pages:
            _page = Page.from_id(int(page)) if page.isdigit() else Page.from_url(page)
            _page.export()
            LockfileManager.record_page(_page)
        sync_removed_pages()


@app.command(help="Export Confluence pages and their descendant pages by ID or URL.")
def pages_with_descendants(
    pages: Annotated[List[str], typer.Argument(help="Page ID(s) or URL(s)")],
    output_path: Annotated[
        Optional[Path],
        typer.Option(
            help="Directory to write exported files to. Overrides config if set."
        ),
    ] = None,
    format: Annotated[
        Optional[str],
        typer.Option(
            "--format",
            "-f",
            help="Output format: markdown, html, or both. Overrides config if set.",
        ),
    ] = None,
) -> None:
    from confluence_markdown_exporter.confluence import Page
    from confluence_markdown_exporter.confluence import sync_removed_pages

    with measure(f"Export pages {', '.join(pages)} with descendants"):
        override_output_path_config(output_path)
        override_export_format(format)
        LockfileManager.init()
        for page in pages:
            _page = Page.from_id(int(page)) if page.isdigit() else Page.from_url(page)
            _page.export_with_descendants()
        sync_removed_pages()


@app.command(help="Export all Confluence pages of one or more spaces.")
def spaces(
    space_keys: Annotated[List[str], typer.Argument()],
    output_path: Annotated[
        Optional[Path],
        typer.Option(
            help="Directory to write exported files to. Overrides config if set."
        ),
    ] = None,
    format: Annotated[
        Optional[str],
        typer.Option(
            "--format",
            "-f",
            help="Output format: markdown, html, or both. Overrides config if set.",
        ),
    ] = None,
) -> None:
    from confluence_markdown_exporter.confluence import Space
    from confluence_markdown_exporter.confluence import sync_removed_pages

    # Personal Confluence spaces start with ~. Exporting them on Windows leads to
    # Powershell expanding tilde to the Users directory, which is handled here
    normalized_space_keys = [handle_powershell_tilde_expansion(key) for key in space_keys]

    with measure(f"Export spaces {', '.join(normalized_space_keys)}"):
        override_output_path_config(output_path)
        override_export_format(format)
        LockfileManager.init()
        for space_key in normalized_space_keys:
            space = Space.from_key(space_key)
            space.export()
        sync_removed_pages()


@app.command(help="Export all Confluence pages across all spaces.")
def all_spaces(
    output_path: Annotated[
        Optional[Path],
        typer.Option(
            help="Directory to write exported files to. Overrides config if set."
        ),
    ] = None,
    format: Annotated[
        Optional[str],
        typer.Option(
            "--format",
            "-f",
            help="Output format: markdown, html, or both. Overrides config if set.",
        ),
    ] = None,
) -> None:
    from confluence_markdown_exporter.confluence import Organization
    from confluence_markdown_exporter.confluence import sync_removed_pages

    with measure("Export all spaces"):
        override_output_path_config(output_path)
        override_export_format(format)
        LockfileManager.init()
        org = Organization.from_api()
        org.export()
        sync_removed_pages()


@app.command(help="Open the interactive configuration menu or display current configuration.")
def config(
    jump_to: Annotated[
        Optional[str],
        typer.Option(help="Jump directly to a config submenu, e.g. 'auth.confluence'"),
    ] = None,
    *,
    show: Annotated[
        bool,
        typer.Option(
            "--show",
            help="Display current configuration as YAML instead of opening the interactive menu",
        ),
    ] = False,
) -> None:
    """Interactive configuration menu or display current configuration."""
    if show:
        current_settings = get_settings()
        json_output = current_settings.model_dump_json(indent=2)
        typer.echo(f"```json\n{json_output}\n```")
    else:
        main_config_menu_loop(jump_to)


@app.command(help="Show the current version of confluence-markdown-exporter.")
def version() -> None:
    """Display the current version."""
    typer.echo(f"confluence-markdown-exporter {__version__}")


if __name__ == "__main__":
    app()
