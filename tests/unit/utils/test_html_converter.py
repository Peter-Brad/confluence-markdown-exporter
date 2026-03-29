"""Unit tests for HTML converter for TinyMCE 5 compatibility."""

from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from bs4 import BeautifulSoup

from confluence_markdown_exporter.confluence import Page
from confluence_markdown_exporter.utils.html_converter import (
    ConfluenceHtmlConverter,
    TinyMCEConfig,
)


class TestTinyMCEConfig:
    """Test TinyMCE configuration."""

    def test_valid_elements_contains_standard_html5(self) -> None:
        """Verify standard HTML5 elements are included."""
        assert "p" in TinyMCEConfig.VALID_ELEMENTS
        assert "div" in TinyMCEConfig.VALID_ELEMENTS
        assert "table" in TinyMCEConfig.VALID_ELEMENTS
        assert "img" in TinyMCEConfig.VALID_ELEMENTS
        assert "a" in TinyMCEConfig.VALID_ELEMENTS
        assert "h1" in TinyMCEConfig.VALID_ELEMENTS
        assert "pre" in TinyMCEConfig.VALID_ELEMENTS
        assert "code" in TinyMCEConfig.VALID_ELEMENTS

    def test_valid_elements_contains_media(self) -> None:
        """Verify media elements are included."""
        assert "video" in TinyMCEConfig.VALID_ELEMENTS
        assert "audio" in TinyMCEConfig.VALID_ELEMENTS
        assert "iframe" in TinyMCEConfig.VALID_ELEMENTS

    def test_valid_attributes_for_links(self) -> None:
        """Verify link attributes are configured."""
        assert "href" in TinyMCEConfig.VALID_ATTRIBUTES["a"]
        assert "target" in TinyMCEConfig.VALID_ATTRIBUTES["a"]
        assert "rel" in TinyMCEConfig.VALID_ATTRIBUTES["a"]

    def test_valid_attributes_for_images(self) -> None:
        """Verify image attributes are configured."""
        assert "src" in TinyMCEConfig.VALID_ATTRIBUTES["img"]
        assert "alt" in TinyMCEConfig.VALID_ATTRIBUTES["img"]
        assert "width" in TinyMCEConfig.VALID_ATTRIBUTES["img"]
        assert "height" in TinyMCEConfig.VALID_ATTRIBUTES["img"]

    def test_valid_attributes_for_tables(self) -> None:
        """Verify table attributes are configured."""
        assert "colspan" in TinyMCEConfig.VALID_ATTRIBUTES["td"]
        assert "rowspan" in TinyMCEConfig.VALID_ATTRIBUTES["td"]
        assert "colspan" in TinyMCEConfig.VALID_ATTRIBUTES["th"]


def _create_mock_settings() -> MagicMock:
    """Create a standard mock settings object."""
    settings = MagicMock()
    settings.export.export_format = "html"
    settings.export.html_embed_images = False
    settings.export.html_wrap_document = False
    settings.export.html_body_source = "export_view"
    settings.export.include_document_title = False
    settings.export.attachment_href = "relative"
    settings.export.page_href = "relative"
    settings.export.output_path = Path("/output")
    return settings


def _create_mock_page() -> MagicMock:
    """Create a standard mock page object."""
    page = MagicMock(spec=Page)
    page.id = 12345
    page.title = "Test Page"
    page.body = "<p>Test content</p>"
    page.body_export = "<p>Test content</p>"
    page.editor2 = ""
    page.attachments = []
    page.ancestors = []
    page.export_path = Path("/output/Test Page.md")
    page.get_attachment_by_file_id = MagicMock(return_value=None)
    page.get_attachment_by_id = MagicMock(return_value=None)
    return page


class TestConfluenceHtmlConverter:
    """Test Confluence HTML conversion."""

    @patch('confluence_markdown_exporter.utils.html_converter.get_settings')
    def test_convert_preserves_basic_html(self, mock_get_settings: MagicMock) -> None:
        """Verify basic HTML is preserved."""
        mock_get_settings.return_value = _create_mock_settings()
        mock_page = _create_mock_page()

        converter = ConfluenceHtmlConverter(mock_page)
        result = converter.convert("<p>Hello <strong>world</strong></p>")

        assert "<p>" in result
        assert "<strong>" in result
        assert "Hello" in result
        assert "world" in result

    @patch('confluence_markdown_exporter.utils.html_converter.get_settings')
    def test_convert_removes_script_tags(self, mock_get_settings: MagicMock) -> None:
        """Verify script tags are removed for security."""
        mock_get_settings.return_value = _create_mock_settings()
        mock_page = _create_mock_page()

        converter = ConfluenceHtmlConverter(mock_page)
        result = converter.convert("<p>Content</p><script>alert('xss')</script>")

        assert "<script>" not in result
        assert "alert" not in result
        assert "Content" in result

    @patch('confluence_markdown_exporter.utils.html_converter.get_settings')
    def test_convert_removes_style_tags(self, mock_get_settings: MagicMock) -> None:
        """Verify style tags are removed."""
        mock_get_settings.return_value = _create_mock_settings()
        mock_page = _create_mock_page()

        converter = ConfluenceHtmlConverter(mock_page)
        result = converter.convert("<style>body { color: red; }</style><p>Content</p>")

        assert "<style>" not in result
        assert "color: red" not in result
        assert "Content" in result

    @patch('confluence_markdown_exporter.utils.html_converter.get_settings')
    def test_convert_info_macro(self, mock_get_settings: MagicMock) -> None:
        """Verify info macro is converted to styled div."""
        mock_get_settings.return_value = _create_mock_settings()
        mock_page = _create_mock_page()

        converter = ConfluenceHtmlConverter(mock_page)
        html = '<div data-macro-name="info"><p>Information message</p></div>'
        result = converter.convert(html)

        assert "confluence-alert" in result
        assert "alert-info" in result

    @patch('confluence_markdown_exporter.utils.html_converter.get_settings')
    def test_convert_warning_macro(self, mock_get_settings: MagicMock) -> None:
        """Verify warning macro is converted to styled div."""
        mock_get_settings.return_value = _create_mock_settings()
        mock_page = _create_mock_page()

        converter = ConfluenceHtmlConverter(mock_page)
        html = '<div data-macro-name="warning"><p>Warning message</p></div>'
        result = converter.convert(html)

        assert "confluence-alert" in result
        assert "alert-warning" in result

    @patch('confluence_markdown_exporter.utils.html_converter.get_settings')
    def test_convert_note_macro(self, mock_get_settings: MagicMock) -> None:
        """Verify note macro is converted to styled div."""
        mock_get_settings.return_value = _create_mock_settings()
        mock_page = _create_mock_page()

        converter = ConfluenceHtmlConverter(mock_page)
        html = '<div data-macro-name="note"><p>Note message</p></div>'
        result = converter.convert(html)

        assert "confluence-alert" in result
        assert "alert-note" in result

    @patch('confluence_markdown_exporter.utils.html_converter.get_settings')
    def test_convert_tip_macro(self, mock_get_settings: MagicMock) -> None:
        """Verify tip macro is converted to styled div."""
        mock_get_settings.return_value = _create_mock_settings()
        mock_page = _create_mock_page()

        converter = ConfluenceHtmlConverter(mock_page)
        html = '<div data-macro-name="tip"><p>Tip message</p></div>'
        result = converter.convert(html)

        assert "confluence-alert" in result
        assert "alert-tip" in result

    @patch('confluence_markdown_exporter.utils.html_converter.get_settings')
    def test_convert_panel_macro(self, mock_get_settings: MagicMock) -> None:
        """Verify panel macro is converted to styled div."""
        mock_get_settings.return_value = _create_mock_settings()
        mock_page = _create_mock_page()

        converter = ConfluenceHtmlConverter(mock_page)
        html = '<div data-macro-name="panel"><p>Panel content</p></div>'
        result = converter.convert(html)

        assert "confluence-panel" in result

    @patch('confluence_markdown_exporter.utils.html_converter.get_settings')
    def test_convert_expand_macro(self, mock_get_settings: MagicMock) -> None:
        """Verify expand macro is converted to details/summary."""
        mock_get_settings.return_value = _create_mock_settings()
        mock_page = _create_mock_page()

        converter = ConfluenceHtmlConverter(mock_page)
        html = '''
        <div class="expand-container" data-macro-name="expand">
            <div class="expand-control-text">Click to expand</div>
            <div class="expand-content"><p>Hidden content</p></div>
        </div>
        '''
        result = converter.convert(html)

        assert "<details>" in result
        assert "<summary>" in result

    @patch('confluence_markdown_exporter.utils.html_converter.get_settings')
    def test_convert_preserves_tables(self, mock_get_settings: MagicMock) -> None:
        """Verify tables are preserved."""
        mock_get_settings.return_value = _create_mock_settings()
        mock_page = _create_mock_page()

        converter = ConfluenceHtmlConverter(mock_page)
        html = '<table><tr><th>Header</th></tr><tr><td>Cell</td></tr></table>'
        result = converter.convert(html)

        assert "<table>" in result
        assert "<th>" in result
        assert "<td>" in result

    @patch('confluence_markdown_exporter.utils.html_converter.get_settings')
    def test_convert_preserves_links(self, mock_get_settings: MagicMock) -> None:
        """Verify external links are preserved."""
        mock_get_settings.return_value = _create_mock_settings()
        mock_page = _create_mock_page()

        converter = ConfluenceHtmlConverter(mock_page)
        html = '<a href="https://example.com">External Link</a>'
        result = converter.convert(html)

        assert '<a href="https://example.com"' in result
        assert "External Link" in result

    @patch('confluence_markdown_exporter.utils.html_converter.get_settings')
    def test_convert_preserves_images(self, mock_get_settings: MagicMock) -> None:
        """Verify images with external URLs are preserved."""
        mock_get_settings.return_value = _create_mock_settings()
        mock_page = _create_mock_page()

        converter = ConfluenceHtmlConverter(mock_page)
        html = '<img src="https://example.com/image.png" alt="test image"/>'
        result = converter.convert(html)

        assert "<img" in result
        assert 'src="https://example.com/image.png"' in result
        assert 'alt="test image"' in result

    @patch('confluence_markdown_exporter.utils.html_converter.get_settings')
    def test_convert_code_block(self, mock_get_settings: MagicMock) -> None:
        """Verify code blocks are preserved."""
        mock_get_settings.return_value = _create_mock_settings()
        mock_page = _create_mock_page()

        converter = ConfluenceHtmlConverter(mock_page)
        html = '<pre><code>def hello():\n    print("Hello")</code></pre>'
        result = converter.convert(html)

        assert "<pre>" in result
        assert "<code>" in result
        assert "def hello():" in result

    @patch('confluence_markdown_exporter.utils.html_converter.get_settings')
    def test_convert_unordered_list(self, mock_get_settings: MagicMock) -> None:
        """Verify unordered lists are preserved."""
        mock_get_settings.return_value = _create_mock_settings()
        mock_page = _create_mock_page()

        converter = ConfluenceHtmlConverter(mock_page)
        html = '<ul><li>Item 1</li><li>Item 2</li></ul>'
        result = converter.convert(html)

        assert "<ul>" in result
        assert "<li>" in result
        assert "Item 1" in result
        assert "Item 2" in result

    @patch('confluence_markdown_exporter.utils.html_converter.get_settings')
    def test_convert_ordered_list(self, mock_get_settings: MagicMock) -> None:
        """Verify ordered lists are preserved."""
        mock_get_settings.return_value = _create_mock_settings()
        mock_page = _create_mock_page()

        converter = ConfluenceHtmlConverter(mock_page)
        html = '<ol><li>Step 1</li><li>Step 2</li></ol>'
        result = converter.convert(html)

        assert "<ol>" in result
        assert "<li>" in result
        assert "Step 1" in result
        assert "Step 2" in result

    @patch('confluence_markdown_exporter.utils.html_converter.get_settings')
    def test_convert_headings(self, mock_get_settings: MagicMock) -> None:
        """Verify headings are preserved."""
        mock_get_settings.return_value = _create_mock_settings()
        mock_page = _create_mock_page()

        converter = ConfluenceHtmlConverter(mock_page)
        html = '<h1>Title</h1><h2>Subtitle</h2><h3>Section</h3>'
        result = converter.convert(html)

        assert "<h1>" in result
        assert "<h2>" in result
        assert "<h3>" in result
        assert "Title" in result
        assert "Subtitle" in result
        assert "Section" in result

    @patch('confluence_markdown_exporter.utils.html_converter.get_settings')
    def test_convert_blockquote(self, mock_get_settings: MagicMock) -> None:
        """Verify blockquotes are preserved."""
        mock_get_settings.return_value = _create_mock_settings()
        mock_page = _create_mock_page()

        converter = ConfluenceHtmlConverter(mock_page)
        html = '<blockquote>This is a quote</blockquote>'
        result = converter.convert(html)

        assert "<blockquote>" in result
        assert "This is a quote" in result

    @patch('confluence_markdown_exporter.utils.html_converter.get_settings')
    def test_convert_inline_formatting(self, mock_get_settings: MagicMock) -> None:
        """Verify inline formatting is preserved."""
        mock_get_settings.return_value = _create_mock_settings()
        mock_page = _create_mock_page()

        converter = ConfluenceHtmlConverter(mock_page)
        html = '<p><strong>bold</strong> <em>italic</em> <code>code</code></p>'
        result = converter.convert(html)

        assert "<strong>" in result
        assert "<em>" in result
        assert "<code>" in result
        assert "bold" in result
        assert "italic" in result

    @patch('confluence_markdown_exporter.utils.html_converter.get_settings')
    def test_convert_to_document_structure(self, mock_get_settings: MagicMock) -> None:
        """Verify full document output structure."""
        mock_get_settings.return_value = _create_mock_settings()
        mock_page = _create_mock_page()

        converter = ConfluenceHtmlConverter(mock_page)
        result = converter.convert_to_document("<p>Content</p>")

        assert "<!DOCTYPE html>" in result
        assert "<html" in result
        assert "<head>" in result
        assert "<body>" in result
        assert "Test Page" in result  # Title in <title> tag

    @patch('confluence_markdown_exporter.utils.html_converter.get_settings')
    def test_convert_to_document_includes_styles(self, mock_get_settings: MagicMock) -> None:
        """Verify document includes CSS styles."""
        mock_get_settings.return_value = _create_mock_settings()
        mock_page = _create_mock_page()

        converter = ConfluenceHtmlConverter(mock_page)
        result = converter.convert_to_document("<p>Content</p>")

        assert "<style>" in result
        assert "font-family" in result

    def test_escape_html_special_characters(self) -> None:
        """Verify HTML special characters are escaped."""
        mock_page = _create_mock_page()
        converter = ConfluenceHtmlConverter(mock_page)
        result = converter._escape_html('<script>alert("xss")</script>')

        assert "&lt;" in result
        assert "&gt;" in result
        assert "&quot;" in result
        assert "<script>" not in result

    @patch('confluence_markdown_exporter.utils.html_converter.get_settings')
    def test_convert_namespaced_elements(self, mock_get_settings: MagicMock) -> None:
        """Verify Confluence namespaced elements are converted to div."""
        mock_get_settings.return_value = _create_mock_settings()
        mock_page = _create_mock_page()

        converter = ConfluenceHtmlConverter(mock_page)
        # BeautifulSoup will parse this, and we test the clean_invalid_elements
        html = '<ac:structured-macro ac:name="test"><p>Content</p></ac:structured-macro>'
        soup = BeautifulSoup(html, "html.parser")
        converter._clean_invalid_elements(soup)
        result = str(soup)

        # Namespaced elements should be converted to div
        assert "ac:structured-macro" not in result


class TestConfluenceHtmlConverterWithAttachments:
    """Test HTML converter with attachment handling."""

    def _create_mock_settings_with_attachments(self) -> MagicMock:
        """Create mock settings with image embedding enabled."""
        settings = _create_mock_settings()
        settings.export.html_embed_images = True
        return settings

    def _create_mock_attachment(self) -> MagicMock:
        """Create mock attachment."""
        attachment = MagicMock()
        attachment.id = "att123"
        attachment.file_id = "file456"
        attachment.title = "test-image.png"
        attachment.export_path = Path("/output/attachments/test-image.png")
        attachment.export = MagicMock()
        return attachment

    def _create_mock_page_with_attachment(self, attachment: MagicMock) -> MagicMock:
        """Create mock page with attachment."""
        page = MagicMock(spec=Page)
        page.id = 12345
        page.title = "Test Page"
        page.body = '<img src="/download/attachments/12345/test-image.png" data-media-id="file456">'
        page.body_export = page.body
        page.editor2 = ""
        page.attachments = [attachment]
        page.ancestors = []
        page.export_path = Path("/output/Test Page.html")
        page.get_attachment_by_file_id = MagicMock(return_value=attachment)
        page.get_attachment_by_id = MagicMock(return_value=attachment)
        return page

    @patch('confluence_markdown_exporter.utils.html_converter.get_settings')
    def test_image_localization(self, mock_get_settings: MagicMock) -> None:
        """Verify images are localized with relative paths."""
        mock_get_settings.return_value = self._create_mock_settings_with_attachments()
        attachment = self._create_mock_attachment()
        mock_page = self._create_mock_page_with_attachment(attachment)

        converter = ConfluenceHtmlConverter(mock_page)
        html = '<img src="/download/test.png" data-media-id="file456" alt="test"/>'
        result = converter.convert(html)

        # Should have relative path
        assert "attachments/test-image.png" in result
        # Should have called export
        attachment.export.assert_called_once()

    @patch('confluence_markdown_exporter.utils.html_converter.get_settings')
    def test_attachment_link_localization(self, mock_get_settings: MagicMock) -> None:
        """Verify attachment links are localized."""
        mock_get_settings.return_value = self._create_mock_settings_with_attachments()
        attachment = self._create_mock_attachment()
        mock_page = self._create_mock_page_with_attachment(attachment)

        converter = ConfluenceHtmlConverter(mock_page)
        html = '<a href="/download/test.txt" data-linked-resource-type="attachment" data-linked-resource-file-id="file456">Download</a>'
        result = converter.convert(html)

        # Should have relative path
        assert "attachments/test-image.png" in result


class TestConfluenceHtmlConverterEdgeCases:
    """Test edge cases in HTML conversion."""

    @patch('confluence_markdown_exporter.utils.html_converter.get_settings')
    def test_empty_content(self, mock_get_settings: MagicMock) -> None:
        """Verify empty content is handled."""
        mock_get_settings.return_value = _create_mock_settings()
        mock_page = _create_mock_page()

        converter = ConfluenceHtmlConverter(mock_page)
        result = converter.convert("")

        assert result == ""

    @patch('confluence_markdown_exporter.utils.html_converter.get_settings')
    def test_complex_nested_structure(self, mock_get_settings: MagicMock) -> None:
        """Verify complex nested HTML is preserved."""
        mock_get_settings.return_value = _create_mock_settings()
        mock_page = _create_mock_page()

        converter = ConfluenceHtmlConverter(mock_page)
        html = '''
        <div>
            <h1>Title</h1>
            <div data-macro-name="info">
                <p>Info paragraph with <strong>bold</strong></p>
                <ul>
                    <li>Item 1</li>
                    <li>Item 2</li>
                </ul>
            </div>
            <table>
                <tr><td>Cell</td></tr>
            </table>
        </div>
        '''
        result = converter.convert(html)

        assert "Title" in result
        assert "Info paragraph" in result
        assert "<strong>" in result
        assert "<ul>" in result
        assert "<table>" in result

    @patch('confluence_markdown_exporter.utils.html_converter.get_settings')
    def test_special_characters_in_content(self, mock_get_settings: MagicMock) -> None:
        """Verify special characters are preserved."""
        mock_get_settings.return_value = _create_mock_settings()
        mock_page = _create_mock_page()

        converter = ConfluenceHtmlConverter(mock_page)
        html = '<p>Special chars: &lt; &gt; &amp; &quot; &#x27;</p>'
        result = converter.convert(html)

        assert "Special chars" in result

    @patch('confluence_markdown_exporter.utils.html_converter.get_settings')
    def test_unknown_macro_is_unwrapped(self, mock_get_settings: MagicMock) -> None:
        """Verify unknown macros are unwrapped but content preserved."""
        mock_get_settings.return_value = _create_mock_settings()
        mock_page = _create_mock_page()

        converter = ConfluenceHtmlConverter(mock_page)
        html = '<div data-macro-name="unknown-macro"><p>Content inside</p></div>'
        result = converter.convert(html)

        assert "Content inside" in result

    @patch('confluence_markdown_exporter.utils.html_converter.get_settings')
    def test_toc_macro_is_converted(self, mock_get_settings: MagicMock) -> None:
        """Verify TOC macro is converted to placeholder."""
        mock_get_settings.return_value = _create_mock_settings()
        mock_page = _create_mock_page()

        converter = ConfluenceHtmlConverter(mock_page)
        html = '<div data-macro-name="toc"></div>'
        result = converter.convert(html)

        assert "confluence-toc" in result

    @patch('confluence_markdown_exporter.utils.html_converter.get_settings')
    def test_inline_task_conversion(self, mock_get_settings: MagicMock) -> None:
        """Verify inline tasks are converted."""
        mock_get_settings.return_value = _create_mock_settings()
        mock_page = _create_mock_page()

        converter = ConfluenceHtmlConverter(mock_page)
        html = '<span data-inline-task-id="123" data-inline-task-status="complete">Task</span>'
        result = converter.convert(html)

        # Should have checkbox character or task content
        assert "☑" in result or "☐" in result or "Task" in result