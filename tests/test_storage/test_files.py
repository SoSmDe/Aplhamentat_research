"""
Tests for FileStorage class (Phase 3.3).

Verifies:
- File save and retrieve operations
- Session directory management
- File size validation
- Cleanup utilities
"""

import asyncio
import os
import shutil
import tempfile
from pathlib import Path

import pytest

from src.storage.files import FileStorage, ALLOWED_FILE_TYPES
from src.tools.errors import (
    DataNotFoundError,
    InvalidInputError,
    StorageFullError,
)


@pytest.fixture
def temp_storage_dir():
    """Create a temporary storage directory."""
    path = tempfile.mkdtemp()
    yield path
    # Cleanup
    if os.path.exists(path):
        shutil.rmtree(path)


@pytest.fixture
def file_storage(temp_storage_dir):
    """Create a FileStorage instance."""
    return FileStorage(temp_storage_dir)


class TestFileStorageInit:
    """Tests for FileStorage initialization."""

    def test_creates_base_directory(self, temp_storage_dir) -> None:
        """FileStorage should create base directory if missing."""
        new_path = os.path.join(temp_storage_dir, "new_subdir")
        storage = FileStorage(new_path)

        assert Path(new_path).exists()

    def test_get_session_dir(self, file_storage) -> None:
        """get_session_dir should return path for session."""
        session_dir = file_storage.get_session_dir("sess_test123")

        assert "sess_test123" in str(session_dir)
        assert session_dir.is_absolute()


class TestFileSave:
    """Tests for file save operations."""

    @pytest.mark.asyncio
    async def test_save_file_creates_file(self, file_storage) -> None:
        """save_file should create file on disk."""
        content = b"Hello, World!"

        path = await file_storage.save_file(
            session_id="sess_test123",
            file_type="pdf",
            content=content,
            filename="test_report.pdf",
        )

        assert Path(path).exists()
        assert Path(path).read_bytes() == content

    @pytest.mark.asyncio
    async def test_save_file_creates_session_directory(self, file_storage) -> None:
        """save_file should create session directory automatically."""
        content = b"Test content"

        await file_storage.save_file(
            session_id="sess_newdir123",
            file_type="pdf",
            content=content,
            filename="report.pdf",
        )

        session_dir = file_storage.get_session_dir("sess_newdir123")
        assert session_dir.exists()

    @pytest.mark.asyncio
    async def test_save_file_validates_file_type(self, file_storage) -> None:
        """save_file should validate file type."""
        with pytest.raises(InvalidInputError) as exc_info:
            await file_storage.save_file(
                session_id="sess_test123",
                file_type="exe",  # Not allowed
                content=b"malicious",
                filename="virus.exe",
            )

        assert "file_type" in exc_info.value.details.get("field", "")

    @pytest.mark.asyncio
    async def test_save_file_validates_filename(self, file_storage) -> None:
        """save_file should validate filename."""
        with pytest.raises(InvalidInputError):
            await file_storage.save_file(
                session_id="sess_test123",
                file_type="pdf",
                content=b"content",
                filename="../escape.pdf",  # Path traversal
            )

    @pytest.mark.asyncio
    async def test_save_file_validates_size(self, file_storage, monkeypatch) -> None:
        """save_file should validate file size limit."""
        def mock_get_limit(name):
            if name == "max_report_size_mb":
                return 1  # 1MB limit
            return 50

        monkeypatch.setattr("src.storage.files.get_limit", mock_get_limit)

        # Create content larger than 1MB
        large_content = b"x" * (2 * 1024 * 1024)  # 2MB

        with pytest.raises(StorageFullError) as exc_info:
            await file_storage.save_file(
                session_id="sess_test123",
                file_type="pdf",
                content=large_content,
                filename="large.pdf",
            )

        assert exc_info.value.details["limit_mb"] == 1

    @pytest.mark.asyncio
    async def test_save_multiple_files(self, file_storage) -> None:
        """Should be able to save multiple files for same session."""
        await file_storage.save_file(
            session_id="sess_test123",
            file_type="pdf",
            content=b"PDF content",
            filename="report.pdf",
        )
        await file_storage.save_file(
            session_id="sess_test123",
            file_type="excel",
            content=b"Excel content",
            filename="data.xlsx",
        )

        files = await file_storage.list_files("sess_test123")
        assert len(files) == 2

    @pytest.mark.asyncio
    async def test_allowed_file_types(self, file_storage) -> None:
        """Should accept all allowed file types."""
        for file_type in ALLOWED_FILE_TYPES:
            await file_storage.save_file(
                session_id="sess_types123",
                file_type=file_type,
                content=b"test content",
                filename=f"test.{file_type}",
            )

        files = await file_storage.list_files("sess_types123")
        assert len(files) == len(ALLOWED_FILE_TYPES)


class TestFileRetrieve:
    """Tests for file retrieve operations."""

    @pytest.mark.asyncio
    async def test_get_file_returns_content(self, file_storage) -> None:
        """get_file should return file content."""
        original = b"Test file content"
        await file_storage.save_file(
            session_id="sess_test123",
            file_type="pdf",
            content=original,
            filename="test.pdf",
        )

        retrieved = await file_storage.get_file("sess_test123", "test.pdf")

        assert retrieved == original

    @pytest.mark.asyncio
    async def test_get_file_raises_for_nonexistent(self, file_storage) -> None:
        """get_file should raise for non-existent file."""
        with pytest.raises(DataNotFoundError) as exc_info:
            await file_storage.get_file("sess_test123", "nonexistent.pdf")

        assert "file" in exc_info.value.details.get("resource_type", "").lower()

    @pytest.mark.asyncio
    async def test_file_exists(self, file_storage) -> None:
        """file_exists should check file existence."""
        await file_storage.save_file(
            session_id="sess_test123",
            file_type="pdf",
            content=b"content",
            filename="exists.pdf",
        )

        assert await file_storage.file_exists("sess_test123", "exists.pdf") is True
        assert await file_storage.file_exists("sess_test123", "missing.pdf") is False


class TestFileList:
    """Tests for file listing."""

    @pytest.mark.asyncio
    async def test_list_files_returns_info(self, file_storage) -> None:
        """list_files should return file information."""
        await file_storage.save_file(
            session_id="sess_test123",
            file_type="pdf",
            content=b"PDF content here",
            filename="report.pdf",
        )

        files = await file_storage.list_files("sess_test123")

        assert len(files) == 1
        file_info = files[0]
        assert file_info["filename"] == "report.pdf"
        assert file_info["file_type"] == "pdf"
        assert file_info["size_bytes"] == 16  # len(b"PDF content here")
        assert "file_path" in file_info
        assert "created_at" in file_info

    @pytest.mark.asyncio
    async def test_list_files_empty_session(self, file_storage) -> None:
        """list_files should return empty list for new session."""
        files = await file_storage.list_files("sess_empty123")
        assert files == []

    @pytest.mark.asyncio
    async def test_list_files_multiple(self, file_storage) -> None:
        """list_files should return all files."""
        await file_storage.save_file(
            "sess_test123", "pdf", b"1", "file1.pdf"
        )
        await file_storage.save_file(
            "sess_test123", "excel", b"22", "file2.xlsx"
        )
        await file_storage.save_file(
            "sess_test123", "csv", b"333", "file3.csv"
        )

        files = await file_storage.list_files("sess_test123")

        assert len(files) == 3
        filenames = {f["filename"] for f in files}
        assert filenames == {"file1.pdf", "file2.xlsx", "file3.csv"}


class TestFileDelete:
    """Tests for file deletion."""

    @pytest.mark.asyncio
    async def test_delete_file(self, file_storage) -> None:
        """delete_file should remove file."""
        await file_storage.save_file(
            session_id="sess_test123",
            file_type="pdf",
            content=b"content",
            filename="delete_me.pdf",
        )

        await file_storage.delete_file("sess_test123", "delete_me.pdf")

        assert await file_storage.file_exists("sess_test123", "delete_me.pdf") is False

    @pytest.mark.asyncio
    async def test_delete_nonexistent_file_is_safe(self, file_storage) -> None:
        """delete_file should not raise for non-existent file."""
        # Should not raise
        await file_storage.delete_file("sess_test123", "nonexistent.pdf")

    @pytest.mark.asyncio
    async def test_delete_session_files(self, file_storage) -> None:
        """delete_session_files should remove all session files."""
        await file_storage.save_file(
            "sess_test123", "pdf", b"1", "file1.pdf"
        )
        await file_storage.save_file(
            "sess_test123", "xlsx", b"2", "file2.xlsx"
        )

        count = await file_storage.delete_session_files("sess_test123")

        assert count == 2
        assert not file_storage.get_session_dir("sess_test123").exists()

    @pytest.mark.asyncio
    async def test_delete_session_files_empty(self, file_storage) -> None:
        """delete_session_files should return 0 for non-existent session."""
        count = await file_storage.delete_session_files("sess_nonexistent")
        assert count == 0


class TestURLGeneration:
    """Tests for URL generation."""

    def test_get_file_url(self, file_storage) -> None:
        """get_file_url should generate URL path."""
        url = file_storage.get_file_url("sess_test123", "report.pdf")
        assert url == "/api/sessions/sess_test123/files/report.pdf"

    def test_get_file_url_custom_base(self, file_storage) -> None:
        """get_file_url should support custom base URL."""
        url = file_storage.get_file_url(
            "sess_test123",
            "report.pdf",
            base_url="/files",
        )
        assert url == "/files/sess_test123/files/report.pdf"


class TestStorageStats:
    """Tests for storage statistics."""

    @pytest.mark.asyncio
    async def test_get_session_storage_size(self, file_storage) -> None:
        """get_session_storage_size should calculate total size."""
        await file_storage.save_file(
            "sess_test123", "pdf", b"x" * 100, "file1.pdf"
        )
        await file_storage.save_file(
            "sess_test123", "xlsx", b"y" * 200, "file2.xlsx"
        )

        size = await file_storage.get_session_storage_size("sess_test123")

        assert size == 300

    @pytest.mark.asyncio
    async def test_get_session_storage_size_empty(self, file_storage) -> None:
        """get_session_storage_size should return 0 for empty session."""
        size = await file_storage.get_session_storage_size("sess_nonexistent")
        assert size == 0


class TestCleanup:
    """Tests for cleanup utilities."""

    @pytest.mark.asyncio
    async def test_cleanup_empty_dirs(self, file_storage) -> None:
        """cleanup_empty_dirs should remove empty directories."""
        # Create some empty directories
        empty_dir = file_storage.get_session_dir("sess_empty1")
        empty_dir.mkdir(parents=True, exist_ok=True)

        # Create a non-empty directory
        await file_storage.save_file(
            "sess_nonempty", "pdf", b"content", "file.pdf"
        )

        count = await file_storage.cleanup_empty_dirs()

        assert count == 1
        assert not empty_dir.exists()
        assert file_storage.get_session_dir("sess_nonempty").exists()


class TestPathSecurity:
    """Tests for path security."""

    def test_session_id_validation_path_traversal(self, file_storage) -> None:
        """get_session_dir should prevent path traversal."""
        with pytest.raises(InvalidInputError):
            file_storage.get_session_dir("../escape")

    def test_session_id_validation_forward_slash(self, file_storage) -> None:
        """get_session_dir should reject forward slashes."""
        with pytest.raises(InvalidInputError):
            file_storage.get_session_dir("path/to/escape")

    def test_session_id_validation_backslash(self, file_storage) -> None:
        """get_session_dir should reject backslashes."""
        with pytest.raises(InvalidInputError):
            file_storage.get_session_dir("path\\to\\escape")

    def test_session_id_validation_empty(self, file_storage) -> None:
        """get_session_dir should reject empty session_id."""
        with pytest.raises(InvalidInputError):
            file_storage.get_session_dir("")
