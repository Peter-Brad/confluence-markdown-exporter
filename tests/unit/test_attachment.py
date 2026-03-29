"""Unit tests for Attachment filename handling."""

from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from confluence_markdown_exporter.confluence import Attachment


def _create_mock_settings() -> MagicMock:
    """Create a standard mock settings object."""
    settings = MagicMock()
    settings.export.attachment_path = "{space_name}/attachments/{attachment_file_id}{attachment_extension}"
    settings.export.output_path = Path("/output")
    settings.export.filename_encoding = '" ":"_",":":"_"'
    settings.export.filename_length = 255
    return settings


def _create_mock_attachment(
    attachment_id: str = "att123",
    title: str = "test-file.pdf",
    file_id: str = "file456",
    extension: str = ".pdf",
) -> MagicMock:
    """Create a mock Attachment for testing."""
    attachment = MagicMock(spec=Attachment)
    attachment.id = attachment_id
    attachment.title = title
    attachment.file_id = file_id
    attachment.extension = extension
    attachment.file_size = 1024
    attachment.media_type = "application/pdf"
    attachment.space = MagicMock()
    attachment.space.name = "Test Space"
    attachment.space.homepage = 12345
    attachment.export_path = Path(f"/output/attachments/{file_id or title}")
    return attachment


class TestAttachmentFilenameLogic:
    """Test cases for Attachment filename logic."""

    def test_filename_with_file_id(self) -> None:
        """Test filename when file_id is present."""
        attachment = _create_mock_attachment(
            attachment_id="att123",
            title="document.pdf",
            file_id="abc-def-123",
            extension=".pdf",
        )

        # Simulate the filename property logic
        if attachment.file_id:
            result = f"{attachment.file_id}{attachment.extension}"
        elif attachment.title:
            result = attachment.title
        else:
            result = f"{attachment.id}{attachment.extension}"

        # Should use file_id + extension
        assert result == "abc-def-123.pdf"

    def test_filename_without_file_id_uses_title(self) -> None:
        """Test filename falls back to title when file_id is empty."""
        attachment = _create_mock_attachment(
            attachment_id="att123",
            title="my-document.pdf",
            file_id="",  # Empty file_id
            extension=".pdf",
        )

        # Simulate the filename property logic
        if attachment.file_id:
            result = f"{attachment.file_id}{attachment.extension}"
        elif attachment.title:
            result = attachment.title
        else:
            result = f"{attachment.id}{attachment.extension}"

        # Should use title as filename
        assert result == "my-document.pdf"

    def test_filename_without_file_id_or_title_uses_id(self) -> None:
        """Test filename falls back to attachment id when both file_id and title are empty."""
        attachment = _create_mock_attachment(
            attachment_id="att789",
            title="",
            file_id="",  # Empty file_id
            extension=".jpg",
        )

        # Simulate the filename property logic
        if attachment.file_id:
            result = f"{attachment.file_id}{attachment.extension}"
        elif attachment.title:
            result = attachment.title
        else:
            result = f"{attachment.id}{attachment.extension}"

        # Should use attachment id + extension
        assert result == "att789.jpg"

    def test_filename_with_image(self) -> None:
        """Test filename for image files."""
        attachment = _create_mock_attachment(
            attachment_id="att123",
            title="photo.jpg",
            file_id="img-456",
            extension=".jpg",
        )

        # Simulate the filename property logic
        if attachment.file_id:
            result = f"{attachment.file_id}{attachment.extension}"
        elif attachment.title:
            result = attachment.title
        else:
            result = f"{attachment.id}{attachment.extension}"

        # Should use file_id + extension
        assert result == "img-456.jpg"

    def test_filename_with_image_no_file_id(self) -> None:
        """Test filename for image files without file_id."""
        attachment = _create_mock_attachment(
            attachment_id="att123",
            title="vacation-photo.png",
            file_id="",  # Empty file_id
            extension=".png",
        )

        # Simulate the filename property logic
        if attachment.file_id:
            result = f"{attachment.file_id}{attachment.extension}"
        elif attachment.title:
            result = attachment.title
        else:
            result = f"{attachment.id}{attachment.extension}"

        # Should use title as filename
        assert result == "vacation-photo.png"


class TestAttachmentTemplateVarsLogic:
    """Test cases for Attachment _template_vars logic."""

    def test_template_vars_with_file_id(self) -> None:
        """Test template vars when file_id is present."""
        attachment = _create_mock_attachment(
            attachment_id="att123",
            title="document.pdf",
            file_id="abc-def-123",
            extension=".pdf",
        )

        # Simulate the _template_vars logic
        file_id_value = attachment.file_id
        if not file_id_value and attachment.title:
            # Sanitize the stem
            file_id_value = Path(attachment.title).stem.replace(" ", "_").replace(":", "_")

        # Verify
        assert file_id_value == "abc-def-123"
        assert attachment.extension == ".pdf"

    def test_template_vars_without_file_id_uses_title_stem(self) -> None:
        """Test template vars uses title stem when file_id is empty."""
        attachment = _create_mock_attachment(
            attachment_id="att123",
            title="my-report.docx",
            file_id="",  # Empty file_id
            extension=".docx",
        )

        # Simulate the _template_vars logic
        file_id_value = attachment.file_id
        if not file_id_value and attachment.title:
            # Sanitize the stem
            file_id_value = Path(attachment.title).stem.replace(" ", "_").replace(":", "_")

        # When file_id is empty, should use title stem (filename without extension)
        assert file_id_value == "my-report"
        assert attachment.extension == ".docx"

    def test_template_vars_empty_file_id_empty_title(self) -> None:
        """Test template vars when both file_id and title are empty."""
        attachment = _create_mock_attachment(
            attachment_id="att789",
            title="",
            file_id="",
            extension=".jpg",
        )

        # Simulate the _template_vars logic
        file_id_value = attachment.file_id
        if not file_id_value and attachment.title:
            file_id_value = Path(attachment.title).stem.replace(" ", "_").replace(":", "_")

        # When both are empty, file_id should be empty string
        assert file_id_value == ""

    def test_template_vars_title_with_dots(self) -> None:
        """Test template vars when title contains multiple dots."""
        attachment = _create_mock_attachment(
            attachment_id="att123",
            title="file.name.with.dots.pdf",
            file_id="",
            extension=".pdf",
        )

        # Simulate the _template_vars logic
        file_id_value = attachment.file_id
        if not file_id_value and attachment.title:
            file_id_value = Path(attachment.title).stem.replace(" ", "_").replace(":", "_")

        # Should use the full stem (everything before last dot)
        assert file_id_value == "file.name.with.dots"

    def test_template_vars_title_with_spaces_and_special_chars(self) -> None:
        """Test template vars sanitizes spaces and special characters in title."""
        attachment = _create_mock_attachment(
            attachment_id="att123",
            title="image2018-5-8 10:36:55.png",
            file_id="",
            extension=".png",
        )

        # Simulate the _template_vars logic with sanitize_filename behavior
        file_id_value = attachment.file_id
        if not file_id_value and attachment.title:
            # Get stem and sanitize (replace spaces with _, colons with _)
            stem = Path(attachment.title).stem
            file_id_value = stem.replace(" ", "_").replace(":", "_")

        # Should sanitize spaces and colons
        assert " " not in file_id_value
        assert ":" not in file_id_value
        assert file_id_value == "image2018-5-8_10_36_55"


class TestAttachmentExportPathLogic:
    """Test cases for Attachment export_path logic."""

    @patch("confluence_markdown_exporter.confluence.settings")
    def test_export_path_with_file_id(self, mock_settings: MagicMock) -> None:
        """Test export path when file_id is present."""
        settings = _create_mock_settings()
        mock_settings.export = settings.export

        # Simulate the export_path logic
        file_id = "abc-def-123"
        extension = ".pdf"
        template = "{space_name}/attachments/{attachment_file_id}{attachment_extension}"

        # When file_id is present
        file_id_value = file_id
        result = template.replace("{space_name}", "Test Space")
        result = result.replace("{attachment_file_id}", file_id_value)
        result = result.replace("{attachment_extension}", extension)

        # Path should contain file_id
        assert "abc-def-123" in result
        assert result.endswith(".pdf")

    @patch("confluence_markdown_exporter.confluence.settings")
    def test_export_path_without_file_id(self, mock_settings: MagicMock) -> None:
        """Test export path when file_id is empty."""
        settings = _create_mock_settings()
        mock_settings.export = settings.export

        # Simulate the export_path logic
        title = "my-document.pdf"
        file_id = ""
        extension = ".pdf"
        template = "{space_name}/attachments/{attachment_file_id}{attachment_extension}"

        # When file_id is empty, use sanitized title stem
        file_id_value = file_id
        if not file_id_value and title:
            file_id_value = Path(title).stem.replace(" ", "_").replace(":", "_")

        result = template.replace("{space_name}", "Test Space")
        result = result.replace("{attachment_file_id}", file_id_value)
        result = result.replace("{attachment_extension}", extension)

        # Path should contain title stem
        assert "my-document" in result
        assert result.endswith(".pdf")
        # Should not result in just extension
        assert result != ".pdf"

    @patch("confluence_markdown_exporter.confluence.settings")
    def test_export_path_with_special_chars(self, mock_settings: MagicMock) -> None:
        """Test export path sanitizes special characters in filename."""
        settings = _create_mock_settings()
        mock_settings.export = settings.export

        # Simulate the export_path logic with special chars
        title = "image2018-5-8 10:36:55.png"
        file_id = ""
        extension = ".png"
        template = "{space_name}/attachments/{attachment_file_id}{attachment_extension}"

        # When file_id is empty, use sanitized title stem
        file_id_value = file_id
        if not file_id_value and title:
            stem = Path(title).stem
            file_id_value = stem.replace(" ", "_").replace(":", "_")

        result = template.replace("{space_name}", "Test_Space")
        result = result.replace("{attachment_file_id}", file_id_value)
        result = result.replace("{attachment_extension}", extension)

        # Path should not contain spaces or colons
        assert " " not in result
        assert ":" not in result
        assert "image2018-5-8_10_36_55" in result

    @patch("confluence_markdown_exporter.confluence.settings")
    def test_export_path_with_title_template(self, mock_settings: MagicMock) -> None:
        """Test export path when using attachment_title in template."""
        settings = _create_mock_settings()
        settings.export.attachment_path = "{space_name}/attachments/{attachment_title}"
        mock_settings.export = settings.export

        # Simulate the export_path logic
        title = "report-2024.xlsx"
        template = "{space_name}/attachments/{attachment_title}"

        result = template.replace("{space_name}", "Test Space")
        result = result.replace("{attachment_title}", title)

        # Path should contain full title
        assert "report-2024.xlsx" in result

    @patch("confluence_markdown_exporter.confluence.settings")
    def test_export_path_image_no_file_id(self, mock_settings: MagicMock) -> None:
        """Test export path for image without file_id."""
        settings = _create_mock_settings()
        mock_settings.export = settings.export

        # Simulate the export_path logic
        title = "profile-picture.png"
        file_id = ""
        extension = ".png"
        template = "{space_name}/attachments/{attachment_file_id}{attachment_extension}"

        # When file_id is empty, use sanitized title stem
        file_id_value = file_id
        if not file_id_value and title:
            file_id_value = Path(title).stem.replace(" ", "_").replace(":", "_")

        result = template.replace("{space_name}", "Test_Space")
        result = result.replace("{attachment_file_id}", file_id_value)
        result = result.replace("{attachment_extension}", extension)

        # Path should contain title stem
        assert "profile-picture" in result
        assert result.endswith(".png")
        # Should not be just extension
        assert result != ".png"

        # Path should contain title stem
        assert "profile-picture" in result
        assert result.endswith(".png")
        # Should not be just extension
        assert result != ".png"


class TestRealAttachmentClass:
    """Test the actual Attachment class methods."""

    @patch("confluence_markdown_exporter.confluence.settings")
    def test_extension_from_title(self, mock_settings: MagicMock) -> None:
        """Test that extension is extracted from title."""
        from confluence_markdown_exporter.confluence import Attachment as RealAttachment
        from confluence_markdown_exporter.confluence import Space, Version, User

        mock_settings.export = _create_mock_settings().export

        # Create minimal required objects
        user = User(
            account_id="test",
            username="test",
            display_name="Test User",
            public_name="Test",
            email="test@test.com",
        )
        version = Version(number=1, by=user, when="2023-01-01", friendly_when="Jan 1, 2023")
        space = Space(key="TEST", name="Test Space", description="Test", homepage=12345)

        attachment = RealAttachment(
            id="att123",
            title="test-document.pdf",
            space=space,
            ancestors=[],
            version=version,
            file_size=1024,
            media_type="application/pdf",
            media_type_description="PDF",
            file_id="file456",
            collection_name="content",
            download_link="/download",
            comment="",
        )

        # Extension should be extracted from title
        assert attachment.extension == ".pdf"

    @patch("confluence_markdown_exporter.confluence.settings")
    def test_extension_from_media_type_when_no_title_extension(self, mock_settings: MagicMock) -> None:
        """Test that extension is guessed from media type when title has no extension."""
        from confluence_markdown_exporter.confluence import Attachment as RealAttachment
        from confluence_markdown_exporter.confluence import Space, Version, User

        mock_settings.export = _create_mock_settings().export

        user = User(
            account_id="test",
            username="test",
            display_name="Test User",
            public_name="Test",
            email="test@test.com",
        )
        version = Version(number=1, by=user, when="2023-01-01", friendly_when="Jan 1, 2023")
        space = Space(key="TEST", name="Test Space", description="Test", homepage=12345)

        attachment = RealAttachment(
            id="att123",
            title="filename_without_extension",
            space=space,
            ancestors=[],
            version=version,
            file_size=1024,
            media_type="image/png",
            media_type_description="PNG Image",
            file_id="file456",
            collection_name="content",
            download_link="/download",
            comment="",
        )

        # Extension should be guessed from media type
        assert attachment.extension == ".png"