"""File manager component for file system operations."""

import os
import shutil
import zipfile
from pathlib import Path
from logging import getLogger
from typing import List, Optional
from uuid import UUID

from fastapi import UploadFile

logger = getLogger(__name__)


class FileInfo:
    """File information data class."""

    def __init__(self, path: str, name: str, size: int, is_directory: bool = False):
        self.path = path
        self.name = name
        self.size = size
        self.is_directory = is_directory

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "path": self.path,
            "name": self.name,
            "size": self.size,
            "is_directory": self.is_directory,
        }


class UploadSession:
    """Upload session tracking."""

    def __init__(
        self, session_id: UUID, project_id: UUID, file_count: int, extracted_path: str
    ):
        self.session_id = session_id
        self.project_id = project_id
        self.file_count = file_count
        self.extracted_path = extracted_path


class FileManager:
    """
    File manager for handling file system operations.

    Provides:
    - Safe path resolution (prevents path traversal attacks)
    - File upload and storage
    - ZIP extraction
    - File discovery
    - File content reading
    - File deletion
    """

    def __init__(self, base_path: str):
        """
        Initialize file manager with base path.

        Args:
            base_path: Base directory for all file operations
        """
        self.base_path = Path(base_path).resolve()
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"FileManager initialized with base path: {self.base_path}")

    def get_safe_path(self, relative_path: str) -> Path:
        """
        Get a safe path within the base directory.

        Prevents path traversal attacks by rejecting absolute paths and ``..``
        components without resolving symlinks.  This allows in-project symlinks
        to point outside the physical base directory while still blocking raw
        traversal attempts.

        Args:
            relative_path: Relative path from base directory

        Returns:
            Path object rooted at base_path (symlinks not followed)

        Raises:
            ValueError: If path is absolute or contains traversal components
        """
        path = Path(relative_path)

        if path.is_absolute():
            logger.warning(f"Absolute path rejected: {relative_path}")
            raise ValueError(f"Path '{relative_path}' must be relative")

        if ".." in path.parts:
            logger.warning(f"Path traversal attempt detected: {relative_path}")
            raise ValueError(f"Path '{relative_path}' contains traversal components")

        return self.base_path / path

    async def save_uploaded_file(self, file: UploadFile, dest_path: str) -> int:
        """
        Save an uploaded file to the destination path.

        Args:
            file: FastAPI UploadFile object
            dest_path: Destination path relative to base directory

        Returns:
            Number of bytes written

        Raises:
            ValueError: If destination path is invalid
        """
        safe_path = self.get_safe_path(dest_path)
        safe_path.parent.mkdir(parents=True, exist_ok=True)

        bytes_written = 0
        with open(safe_path, "wb") as f:
            while content := await file.read(1024 * 1024):  # Read in 1MB chunks
                bytes_written += f.write(content)

        logger.info(f"Saved uploaded file: {dest_path} ({bytes_written} bytes)")
        return bytes_written

    def extract_zip(self, zip_path: str, dest_path: str) -> int:
        """
        Extract a ZIP file to the destination directory.

        Args:
            zip_path: Path to ZIP file relative to base directory
            dest_path: Destination directory relative to base directory

        Returns:
            Number of files extracted

        Raises:
            zipfile.BadZipFile: If file is not a valid ZIP
            ValueError: If paths are invalid
        """
        safe_zip_path = self.get_safe_path(zip_path)
        safe_dest_path = self.get_safe_path(dest_path)
        safe_dest_path.mkdir(parents=True, exist_ok=True)

        files_extracted = 0
        with zipfile.ZipFile(safe_zip_path, "r") as zip_ref:
            for member in zip_ref.namelist():
                # Skip directory entries
                if member.endswith("/"):
                    continue

                # Extract file
                zip_ref.extract(member, safe_dest_path)
                files_extracted += 1

        logger.info(f"Extracted {files_extracted} files from {zip_path} to {dest_path}")
        return files_extracted

    def discover_files(
        self, project_path: str, extensions: Optional[List[str]] = None
    ) -> List[str]:
        """
        Discover files in a project directory, following symlinks with cycle detection.

        Args:
            project_path: Project directory path relative to base directory
            extensions: List of file extensions to include (e.g., ['.py', '.js'])

        Returns:
            List of file paths relative to base directory
        """
        safe_path = self.get_safe_path(project_path)

        if not safe_path.exists():
            logger.warning(f"Project path does not exist: {project_path}")
            return []

        visited_real_dirs: set = set()
        files = []
        for root, dirs, filenames in os.walk(safe_path, followlinks=True):
            real_root = os.path.realpath(root)
            if real_root in visited_real_dirs:
                dirs[:] = []
                continue
            visited_real_dirs.add(real_root)

            for filename in filenames:
                file_path = Path(root) / filename

                # Filter by extension if specified
                if extensions:
                    if file_path.suffix.lower() not in [
                        ext.lower() for ext in extensions
                    ]:
                        continue

                # Get relative path
                rel_path = str(file_path.relative_to(self.base_path))
                files.append(rel_path)

        logger.info(f"Discovered {len(files)} files in {project_path}")
        return files

    def get_file_content(self, file_path: str) -> str:
        """
        Read file content.

        Args:
            file_path: File path relative to base directory

        Returns:
            File content as string

        Raises:
            FileNotFoundError: If file does not exist
            ValueError: If path is invalid
        """
        safe_path = self.get_safe_path(file_path)

        if not safe_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if safe_path.is_dir():
            raise IsADirectoryError(f"Path is a directory: {file_path}")

        with open(safe_path, "r", encoding="utf-8") as f:
            content = f.read()

        logger.debug(f"Read file content: {file_path}")
        return content

    def delete_file(self, file_path: str) -> None:
        """
        Delete a file.

        Args:
            file_path: File path relative to base directory

        Raises:
            FileNotFoundError: If file does not exist
            ValueError: If path is invalid
        """
        safe_path = self.get_safe_path(file_path)

        if not safe_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if safe_path.is_dir():
            raise IsADirectoryError(f"Path is a directory: {file_path}")

        safe_path.unlink()
        logger.info(f"Deleted file: {file_path}")

    def create_directory(self, dir_path: str) -> None:
        """
        Create a directory.

        Args:
            dir_path: Directory path relative to base directory

        Raises:
            ValueError: If path is invalid
            FileExistsError: If directory already exists
        """
        safe_path = self.get_safe_path(dir_path)
        safe_path.mkdir(parents=True, exist_ok=False)
        logger.info(f"Created directory: {dir_path}")

    def list_files(self, dir_path: str, relative_path: str = None) -> List[FileInfo]:
        """
        List files in a directory.

        Args:
            dir_path: Directory path relative to base directory

        Returns:
            List of FileInfo objects

        Raises:
            NotADirectoryError: If path is not a directory
            ValueError: If path is invalid
        """
        safe_path = self.get_safe_path(dir_path)

        if not safe_path.exists():
            return []

        if not safe_path.is_dir():
            raise NotADirectoryError(f"Path is not a directory: {dir_path}")

        files = []
        base_path = self.base_path if relative_path is None else self.get_safe_path(relative_path)
        for item in safe_path.iterdir():
            rel_path = str(item.relative_to(base_path))
            try:
                if item.is_dir():
                    files.append(FileInfo(rel_path, item.name, 0, is_directory=True))
                elif item.is_file():
                    files.append(FileInfo(rel_path, item.name, item.stat().st_size))
                else:
                    # Broken symlink or unresolvable path — skip silently
                    logger.warning(f"Skipping unresolvable entry: {item}")
            except OSError as e:
                logger.warning(f"Error accessing {item}: {e}")

        return files

    def delete_directory(self, dir_path: str, recursive: bool = False) -> None:
        """
        Delete a directory.

        Args:
            dir_path: Directory path relative to base directory
            recursive: If True, delete recursively

        Raises:
            ValueError: If path is invalid
            OSError: If directory is not empty and recursive is False
        """
        safe_path = self.get_safe_path(dir_path)

        if not safe_path.exists():
            logger.warning(f"Directory does not exist: {dir_path}")
            return

        if recursive:
            shutil.rmtree(safe_path)
            logger.info(f"Deleted directory recursively: {dir_path}")
        else:
            safe_path.rmdir()
            logger.info(f"Deleted directory: {dir_path}")
