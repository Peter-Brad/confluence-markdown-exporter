"""HTML converter for Confluence content to TinyMCE 5 compatible HTML.

This module provides functionality to convert Confluence HTML content
to standard HTML that is compatible with TinyMCE 5 editor.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING

from bs4 import BeautifulSoup
from bs4 import Tag

from confluence_markdown_exporter.utils.app_data_store import get_settings

if TYPE_CHECKING:
    from confluence_markdown_exporter.confluence import Attachment
    from confluence_markdown_exporter.confluence import Page

logger = logging.getLogger(__name__)


class TinyMCEConfig:
    """Configuration for TinyMCE 5 valid elements and attributes.

    Based on TinyMCE 5 default schema and common extensions.
    Reference: https://www.tiny.cloud/docs/tinymce/6/content-formatting/
    """

    # Valid HTML5 elements for TinyMCE
    VALID_ELEMENTS = {
        # Block elements
        "p",
        "div",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "blockquote",
        "pre",
        "address",
        "article",
        "aside",
        "section",
        "nav",
        "header",
        "footer",
        "main",
        "figure",
        "figcaption",
        "details",
        "summary",
        # Lists
        "ul",
        "ol",
        "li",
        "dl",
        "dt",
        "dd",
        # Tables
        "table",
        "thead",
        "tbody",
        "tfoot",
        "tr",
        "th",
        "td",
        "caption",
        "colgroup",
        "col",
        # Inline elements
        "a",
        "strong",
        "em",
        "b",
        "i",
        "u",
        "s",
        "strike",
        "span",
        "br",
        "code",
        "kbd",
        "samp",
        "var",
        "sub",
        "sup",
        "mark",
        "small",
        "abbr",
        "cite",
        "dfn",
        "q",
        "time",
        "data",
        "ruby",
        "rt",
        "rp",
        "bdi",
        "bdo",
        # Media
        "img",
        "picture",
        "source",
        "audio",
        "video",
        "track",
        # Semantic
        "wbr",
        "ins",
        "del",
        # Special
        "hr",
        "iframe",
    }

    # Attributes to preserve per element
    VALID_ATTRIBUTES = {
        "*": ["id", "class", "title", "style", "data-*"],
        "a": ["href", "target", "rel", "download", "hreflang", "type"],
        "img": ["src", "alt", "width", "height", "loading", "srcset", "sizes"],
        "table": ["border", "cellpadding", "cellspacing", "width", "summary"],
        "td": ["colspan", "rowspan", "width", "height", "headers"],
        "th": ["colspan", "rowspan", "width", "height", "headers", "scope"],
        "col": ["span", "width"],
        "colgroup": ["span"],
        "ol": ["start", "type", "reversed"],
        "ul": ["type"],
        "li": ["value"],
        "blockquote": ["cite"],
        "q": ["cite"],
        "time": ["datetime"],
        "data": ["value"],
        "abbr": ["title"],
        "iframe": [
            "src",
            "width",
            "height",
            "frameborder",
            "allow",
            "allowfullscreen",
        ],
        "video": [
            "src",
            "width",
            "height",
            "controls",
            "autoplay",
            "loop",
            "muted",
            "poster",
        ],
        "audio": ["src", "controls", "autoplay", "loop", "muted"],
        "source": ["src", "type", "srcset", "sizes", "media"],
        "track": ["src", "kind", "srclang", "label", "default"],
    }


class ConfluenceHtmlConverter:
    """Convert Confluence HTML to TinyMCE 5 compatible HTML.

    Handles:
    - Confluence-specific elements (macros, attachments, links)
    - Image localization
    - Style preservation
    - Link transformation
    """

    def __init__(self, page: Page) -> None:
        self.page = page
        self.tinymce_config = TinyMCEConfig()

    def convert(self, html_content: str) -> str:
        """Main conversion method.

        Args:
            html_content: Raw Confluence HTML content

        Returns:
            TinyMCE 5 compatible HTML
        """
        soup = BeautifulSoup(html_content, "html.parser")

        # Process the DOM tree
        self._process_confluence_elements(soup)
        self._process_images(soup)
        self._process_links(soup)
        self._clean_invalid_elements(soup)

        return str(soup)

    def convert_to_document(self, html_content: str) -> str:
        """Convert to a complete HTML document.

        Returns:
            Full HTML document with head, body structure
        """
        settings = get_settings()
        body_content = self.convert(html_content)

        # Build custom head content
        custom_head = settings.export.html_custom_head_content if hasattr(settings.export, "html_custom_head_content") else ""

        # Build complete document
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self._escape_html(self.page.title)}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; max-width: 900px; margin: 0 auto; padding: 20px; }}
        h1, h2, h3, h4, h5, h6 {{ margin-top: 1.5em; margin-bottom: 0.5em; }}
        table {{ border-collapse: collapse; margin: 1em 0; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f4f4f4; }}
        img {{ max-width: 100%; height: auto; }}
        pre {{ background-color: #f4f4f4; padding: 1em; overflow-x: auto; border-radius: 4px; }}
        code {{ background-color: #f4f4f4; padding: 0.2em 0.4em; border-radius: 3px; }}
        blockquote {{ border-left: 4px solid #ddd; margin: 1em 0; padding-left: 1em; color: #666; }}
        .confluence-alert {{ padding: 1em; margin: 1em 0; border-radius: 4px; }}
        .alert-info {{ background-color: #e8f4fd; border-left: 4px solid #0066cc; }}
        .alert-note {{ background-color: #fff3e0; border-left: 4px solid #ff9800; }}
        .alert-warning {{ background-color: #ffebee; border-left: 4px solid #f44336; }}
        .alert-tip {{ background-color: #e8f5e9; border-left: 4px solid #4caf50; }}
    </style>
    {custom_head}
</head>
<body>
{body_content}
</body>
</html>"""

    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters."""
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )

    def _process_confluence_elements(self, soup: BeautifulSoup) -> None:
        """Handle Confluence-specific elements."""
        # Handle macros (data-macro-name attributes)
        for el in soup.find_all(attrs={"data-macro-name": True}):
            self._convert_macro(el)

        # Handle inline tasks
        for el in soup.find_all(attrs={"data-inline-task-id": True}):
            self._convert_inline_task(el)

        # Handle expand blocks
        for el in soup.find_all(class_="expand-container"):
            self._convert_expand_block(el)

        # Handle column layouts
        for el in soup.find_all(class_="columnLayout"):
            self._convert_column_layout(el)

    def _convert_macro(self, el: Tag) -> None:
        """Convert Confluence macro to HTML equivalent."""
        macro_name = el.get("data-macro-name", "")

        macro_handlers = {
            "info": lambda e: self._convert_alert_macro(e, "info"),
            "note": lambda e: self._convert_alert_macro(e, "note"),
            "warning": lambda e: self._convert_alert_macro(e, "warning"),
            "tip": lambda e: self._convert_alert_macro(e, "tip"),
            "panel": lambda e: self._convert_panel_macro(e),
            "code": lambda e: self._convert_code_macro(e),
            "toc": lambda e: self._convert_toc_macro(e),
            "expand": lambda e: self._convert_expand_macro(e),
            "attachments": lambda e: self._convert_attachments_macro(e),
        }

        if macro_name in macro_handlers:
            macro_handlers[macro_name](el)
        else:
            # Keep content but remove macro wrapper
            self._unwrap_element(el, f"confluence-macro-{macro_name}")

    def _convert_alert_macro(self, el: Tag, alert_type: str) -> None:
        """Convert alert/info macros to styled divs."""
        el.name = "div"
        existing_classes = el.get("class", [])
        if isinstance(existing_classes, str):
            existing_classes = existing_classes.split()
        el["class"] = existing_classes + ["confluence-alert", f"alert-{alert_type}"]

        # Add visual styling
        styles = {
            "info": "background-color: #e8f4fd; border-left: 4px solid #0066cc; padding: 1em; margin: 1em 0;",
            "note": "background-color: #fff3e0; border-left: 4px solid #ff9800; padding: 1em; margin: 1em 0;",
            "warning": "background-color: #ffebee; border-left: 4px solid #f44336; padding: 1em; margin: 1em 0;",
            "tip": "background-color: #e8f5e9; border-left: 4px solid #4caf50; padding: 1em; margin: 1em 0;",
        }
        el["style"] = styles.get(alert_type, "")

    def _convert_panel_macro(self, el: Tag) -> None:
        """Convert panel macro to styled div."""
        el.name = "div"
        existing_classes = el.get("class", [])
        if isinstance(existing_classes, str):
            existing_classes = existing_classes.split()
        el["class"] = existing_classes + ["confluence-panel"]
        el["style"] = "background-color: #f5f5f5; border: 1px solid #ddd; padding: 1em; margin: 1em 0; border-radius: 4px;"

    def _convert_code_macro(self, el: Tag) -> None:
        """Convert code macro to pre/code elements."""
        # Get language from macro parameters
        lang = ""
        params = el.get("data-macro-params", {})
        if isinstance(params, dict):
            lang = params.get("language", "")

        # Find the code content
        code_content = el.get_text()

        pre = BeautifulSoup().new_tag("pre")
        code = BeautifulSoup().new_tag("code")
        if lang:
            code["class"] = f"language-{lang}"

        code.string = code_content
        pre.append(code)
        el.replace_with(pre)

    def _convert_toc_macro(self, el: Tag) -> None:
        """Convert TOC macro to a placeholder div."""
        el.name = "div"
        el["class"] = "confluence-toc"
        el["style"] = "background-color: #f9f9f9; border: 1px solid #ddd; padding: 1em; margin: 1em 0;"
        el.string = "[Table of Contents - generated from page structure]"

    def _convert_expand_macro(self, el: Tag) -> None:
        """Convert expand macro to details/summary elements."""
        details = BeautifulSoup().new_tag("details")
        summary = BeautifulSoup().new_tag("summary")

        # Find title
        title_el = el.find(class_="expand-control-text")
        summary.string = title_el.get_text() if title_el else "Click to expand..."

        # Find content
        content_el = el.find(class_="expand-content")

        details.append(summary)
        if content_el:
            for child in list(content_el.children):
                details.append(child.extract() if hasattr(child, "extract") else child)

        el.replace_with(details)

    def _convert_attachments_macro(self, el: Tag) -> None:
        """Convert attachments macro to a list of attachment links."""
        # Create a simple list of attachments
        div = BeautifulSoup().new_tag("div")
        div["class"] = "confluence-attachments"
        div["style"] = "margin: 1em 0;"

        # Add heading
        heading = BeautifulSoup().new_tag("h4")
        heading.string = "Attachments"
        div.append(heading)

        # List attachments if available
        if hasattr(self.page, "attachments") and self.page.attachments:
            ul = BeautifulSoup().new_tag("ul")
            for att in self.page.attachments:
                li = BeautifulSoup().new_tag("li")
                a = BeautifulSoup().new_tag("a")
                a.string = att.title
                # Set href to relative path
                if hasattr(att, "export_path"):
                    self._set_attachment_link(a, att)
                li.append(a)
                ul.append(li)
            div.append(ul)
        else:
            p = BeautifulSoup().new_tag("p")
            p.string = "No attachments."
            div.append(p)

        el.replace_with(div)

    def _convert_inline_task(self, el: Tag) -> None:
        """Convert inline task to checkbox format."""
        task_id = el.get("data-inline-task-id", "")
        status = el.get("data-inline-task-status", "incomplete")

        # Create a checkbox representation
        checkbox = "☑" if status == "complete" else "☐"
        el.insert_before(BeautifulSoup(f"<span>{checkbox} </span>", "html.parser"))

    def _convert_expand_block(self, el: Tag) -> None:
        """Convert expand block to details/summary."""
        details = BeautifulSoup().new_tag("details")
        summary = BeautifulSoup().new_tag("summary")

        # Find title element
        title_el = el.find(class_="expand-control-text")
        if title_el:
            summary.string = title_el.get_text()

        # Move content
        content_el = el.find(class_="expand-content")
        if content_el:
            for child in list(content_el.children):
                details.append(child.extract() if hasattr(child, "extract") else child)

        details.insert(0, summary)
        el.replace_with(details)

    def _convert_column_layout(self, el: Tag) -> None:
        """Convert column layout to a simple div structure."""
        el.name = "div"
        el["class"] = "column-layout"
        el["style"] = "display: flex; gap: 1em; margin: 1em 0;"

    def _process_images(self, soup: BeautifulSoup) -> None:
        """Process images and localize if configured."""
        for img in soup.find_all("img"):
            self._convert_image(img)

    def _convert_image(self, img: Tag) -> None:
        """Convert image element with local path support."""

        settings = get_settings()

        # Find attachment
        attachment = None
        fid = img.get("data-media-id")
        if fid:
            attachment = self.page.get_attachment_by_file_id(str(fid))

        if not attachment:
            aid = img.get("data-linked-resource-id")
            if aid:
                attachment = self.page.get_attachment_by_id(str(aid))

        if attachment and settings.export.html_embed_images:
            # Calculate relative path
            self._set_image_src(img, attachment)
            # Ensure attachment is exported
            attachment.export()
        # else: keep original URL if no attachment found

        # Clean up Confluence-specific attributes
        for attr in list(img.attrs.keys()):
            if attr.startswith("data-") and attr not in ("data-src",):
                del img[attr]

    def _set_image_src(self, img: Tag, attachment: Attachment) -> None:
        """Set image src to local attachment path."""

        settings = get_settings()
        page_path = self.page.export_path
        att_path = attachment.export_path

        if settings.export.attachment_href == "relative":
            relative_path = os.path.relpath(att_path, page_path.parent)
        else:
            relative_path = "/" + str(att_path).lstrip("/")

        img["src"] = relative_path.replace(" ", "%20")

    def _process_links(self, soup: BeautifulSoup) -> None:
        """Process page and attachment links."""
        for a in soup.find_all("a"):
            self._convert_link(a)

    def _convert_link(self, a: Tag) -> None:
        """Convert link element."""

        resource_type = a.get("data-linked-resource-type", "")

        # Handle page links
        if "page" in str(resource_type).lower():
            page_id = a.get("data-linked-resource-id", "")
            if page_id and page_id != "null":
                self._set_page_link(a, page_id)

        # Handle attachment links
        elif "attachment" in str(resource_type).lower():
            attachment = None
            fid = a.get("data-linked-resource-file-id")
            if fid:
                attachment = self.page.get_attachment_by_file_id(str(fid))
            if not attachment:
                aid = a.get("data-linked-resource-id")
                if aid:
                    attachment = self.page.get_attachment_by_id(str(aid))

            if attachment:
                self._set_attachment_link(a, attachment)
                attachment.export()

        # Clean up Confluence-specific attributes
        for attr in list(a.attrs.keys()):
            if attr.startswith("data-") and attr not in ("data-src",):
                del a[attr]

    def _set_page_link(self, a: Tag, page_id: str) -> None:
        """Set link href to local page path."""
        try:
            from confluence_markdown_exporter.confluence import Page

            target_page = Page.from_id(int(page_id))
            if target_page.title == "Page not accessible":
                return

            settings = get_settings()
            page_path = self.page.export_path

            # Determine target path based on export format
            if settings.export.export_format == "html":
                target_path = target_page.export_path.with_suffix(".html")
            else:
                target_path = target_page.export_path

            if settings.export.page_href == "relative":
                relative_path = os.path.relpath(target_path, page_path.parent)
            else:
                relative_path = "/" + str(target_path).lstrip("/")

            a["href"] = relative_path.replace(" ", "%20")
        except Exception as e:
            logger.warning(f"Failed to convert page link for page {page_id}: {e}")

    def _set_attachment_link(self, a: Tag, attachment: Attachment) -> None:
        """Set link href to local attachment path."""

        settings = get_settings()
        page_path = self.page.export_path
        att_path = attachment.export_path

        if settings.export.attachment_href == "relative":
            relative_path = os.path.relpath(att_path, page_path.parent)
        else:
            relative_path = "/" + str(att_path).lstrip("/")

        a["href"] = relative_path.replace(" ", "%20")

    def _clean_invalid_elements(self, soup: BeautifulSoup) -> None:
        """Remove or transform elements not valid for TinyMCE."""
        # Remove script tags (security)
        for script in soup.find_all("script"):
            script.decompose()

        # Remove style tags (will be replaced by document styles)
        for style in soup.find_all("style"):
            style.decompose()

        # Convert Confluence namespaced elements
        for el in soup.find_all(True):
            if ":" in el.name:
                # Handle namespaced elements
                el.name = "div"

    def _unwrap_element(self, el: Tag, class_name: str = "") -> None:
        """Unwrap element, keeping its contents."""
        if class_name:
            existing_classes = el.get("class", [])
            if isinstance(existing_classes, str):
                existing_classes = existing_classes.split()
            el["class"] = existing_classes + [class_name]
        el.unwrap()