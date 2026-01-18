"""
Ralph Deep Research - File Storage

File-based storage for generated reports (PDF, Excel, PowerPoint).
Based on specs/ARCHITECTURE.md.

Directory structure:
    {base_path}/{session_id}/{filename}

Example:
    ./reports/sess_a1b2c3d4e5f6/research_report.pdf
    ./reports/sess_a1b2c3d4e5f6/data_export.xlsx

Why file storage:
- Reports can be large (up to 20MB per spec)
- Need to serve files via HTTP
- Easy backup and migration

Usage:
    storage = FileStorage("./reports")

    # Save a file
    path = await storage.save_file(
        session_id="sess_123",
        file_type="pdf",
        content=pdf_bytes,
        filename="research_report.pdf"
    )

    # Get file
    content = await storage.get_file("sess_123", "research_report.pdf")
"""

from __future__ import annotations

import asyncio
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.tools.errors import (
    DataNotFoundError,
    InvalidInputError,
    StorageFullError,
)
from src.tools.logging import get_logger
from src.config.timeouts import get_limit

logger = get_logger(__name__)


def _utc_now() -> datetime:
    """Return current UTC time with timezone info."""
    return datetime.now(timezone.utc)


# Allowed file types and their extensions
ALLOWED_FILE_TYPES = frozenset({
    "pdf",
    "excel",
    "xlsx",
    "pptx",
    "csv",
    "json",
})


class FileStorage:
    """
    File storage for session reports and exports.

    Features:
    - Session-isolated file storage
    - Automatic directory creation
    - File size tracking
    - URL generation for serving
    - Cleanup utilities
    """

    def __init__(self, base_path: str = "./reports") -> None:
        """
        Initialize file storage.

        Args:
            base_path: Root directory for file storage
        """
        self._base_path = Path(base_path).resolve()
        self._ensure_base_dir()

    def _ensure_base_dir(self) -> None:
        """Ensure base directory exists."""
        self._base_path.mkdir(parents=True, exist_ok=True)

    def get_session_dir(self, session_id: str) -> Path:
        """
        Get directory path for a session.

        Args:
            session_id: Session identifier

        Returns:
            Path to session directory
        """
        # Validate session_id to prevent path traversal
        if not session_id or ".." in session_id or "/" in session_id or "\\" in session_id:
            raise InvalidInputError(
                message="Invalid session_id",
                field="session_id",
                value=session_id,
            )

        return self._base_path / session_id

    def _ensure_session_dir(self, session_id: str) -> Path:
        """Ensure session directory exists and return path."""
        session_dir = self.get_session_dir(session_id)
        session_dir.mkdir(parents=True, exist_ok=True)
        return session_dir

    async def save_file(
        self,
        session_id: str,
        file_type: str,
        content: bytes,
        filename: str,
    ) -> str:
        """
        Save a file to session storage.

        Args:
            session_id: Session identifier
            file_type: Type of file (pdf, excel, pptx, csv)
            content: File content as bytes
            filename: Filename to use

        Returns:
            Absolute path to saved file

        Raises:
            InvalidInputError: If file type or filename invalid
            StorageFullError: If file exceeds size limit
        """
        # Validate file type
        file_type_lower = file_type.lower()
        if file_type_lower not in ALLOWED_FILE_TYPES:
            raise InvalidInputError(
                message=f"Invalid file type: {file_type}",
                field="file_type",
                value=file_type,
                expected=", ".join(sorted(ALLOWED_FILE_TYPES)),
            )

        # Validate filename
        if not filename or ".." in filename or "/" in filename or "\\" in filename:
            raise InvalidInputError(
                message="Invalid filename",
                field="filename",
                value=filename,
            )

        # Check file size limit
        max_size_mb = get_limit("max_report_size_mb")
        max_size_bytes = max_size_mb * 1024 * 1024
        if len(content) > max_size_bytes:
            raise StorageFullError(
                message=f"File exceeds maximum size ({max_size_mb}MB)",
                storage_type="file",
                current_size_mb=len(content) / (1024 * 1024),
                limit_mb=max_size_mb,
            )

        # Ensure directory exists
        session_dir = self._ensure_session_dir(session_id)
        file_path = session_dir / filename

        # Write file asynchronously
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            self._write_file,
            file_path,
            content,
        )

        logger.info(
            "File saved",
            session_id=session_id,
            filename=filename,
            file_type=file_type,
            size_bytes=len(content),
        )

        return str(file_path)

    @staticmethod
    def _write_file(path: Path, content: bytes) -> None:
        """Synchronous file write helper."""
        path.write_bytes(content)

    async def get_file(
        self,
        session_id: str,
        filename: str,
    ) -> bytes:
        """
        Read a file from session storage.

        Args:
            session_id: Session identifier
            filename: Filename to read

        Returns:
            File content as bytes

        Raises:
            DataNotFoundError: If file doesn't exist
        """
        session_dir = self.get_session_dir(session_id)
        file_path = session_dir / filename

        if not file_path.exists():
            raise DataNotFoundError(
                message=f"File not found: {filename}",
                resource_type="file",
                resource_id=f"{session_id}/{filename}",
            )

        # Read file asynchronously
        loop = asyncio.get_event_loop()
        content = await loop.run_in_executor(
            None,
            file_path.read_bytes,
        )

        return content

    async def file_exists(
        self,
        session_id: str,
        filename: str,
    ) -> bool:
        """
        Check if a file exists.

        Args:
            session_id: Session identifier
            filename: Filename to check

        Returns:
            True if file exists
        """
        session_dir = self.get_session_dir(session_id)
        file_path = session_dir / filename
        return file_path.exists()

    async def list_files(self, session_id: str) -> list[dict[str, Any]]:
        """
        List all files for a session.

        Args:
            session_id: Session identifier

        Returns:
            List of file info dicts with name, type, size, created_at
        """
        session_dir = self.get_session_dir(session_id)

        if not session_dir.exists():
            return []

        files = []
        for file_path in session_dir.iterdir():
            if file_path.is_file():
                stat = file_path.stat()
                files.append({
                    "filename": file_path.name,
                    "file_type": self._guess_file_type(file_path.name),
                    "file_path": str(file_path),
                    "size_bytes": stat.st_size,
                    "created_at": datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc),
                })

        return sorted(files, key=lambda f: f["created_at"])

    @staticmethod
    def _guess_file_type(filename: str) -> str:
        """Guess file type from extension."""
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        type_map = {
            "pdf": "pdf",
            "xlsx": "excel",
            "xls": "excel",
            "pptx": "pptx",
            "ppt": "pptx",
            "csv": "csv",
            "json": "json",
        }
        return type_map.get(ext, "unknown")

    async def delete_file(
        self,
        session_id: str,
        filename: str,
    ) -> None:
        """
        Delete a specific file.

        Args:
            session_id: Session identifier
            filename: Filename to delete
        """
        session_dir = self.get_session_dir(session_id)
        file_path = session_dir / filename

        if file_path.exists():
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, file_path.unlink)

            logger.info(
                "File deleted",
                session_id=session_id,
                filename=filename,
            )

    async def delete_session_files(self, session_id: str) -> int:
        """
        Delete all files for a session.

        Args:
            session_id: Session identifier

        Returns:
            Number of files deleted
        """
        session_dir = self.get_session_dir(session_id)

        if not session_dir.exists():
            return 0

        # Count files before deletion
        file_count = sum(1 for _ in session_dir.iterdir() if _.is_file())

        # Delete directory and contents
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            shutil.rmtree,
            session_dir,
        )

        logger.info(
            "Session files deleted",
            session_id=session_id,
            count=file_count,
        )

        return file_count

    def get_file_url(
        self,
        session_id: str,
        filename: str,
        base_url: str = "/api/sessions",
    ) -> str:
        """
        Generate URL for accessing a file.

        Args:
            session_id: Session identifier
            filename: Filename
            base_url: Base URL prefix

        Returns:
            URL path for the file
        """
        return f"{base_url}/{session_id}/files/{filename}"

    async def get_session_storage_size(self, session_id: str) -> int:
        """
        Calculate total storage used by a session.

        Args:
            session_id: Session identifier

        Returns:
            Total size in bytes
        """
        session_dir = self.get_session_dir(session_id)

        if not session_dir.exists():
            return 0

        total = 0
        for file_path in session_dir.iterdir():
            if file_path.is_file():
                total += file_path.stat().st_size

        return total

    async def cleanup_empty_dirs(self) -> int:
        """
        Remove empty session directories.

        Returns:
            Number of directories removed
        """
        count = 0
        for item in self._base_path.iterdir():
            if item.is_dir() and not any(item.iterdir()):
                item.rmdir()
                count += 1

        if count > 0:
            logger.info("Empty directories cleaned up", count=count)

        return count
