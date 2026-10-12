"""File service for file upload and management operations."""

import zipfile
from logging import getLogger
from typing import List
from uuid import UUID, uuid4

from fastapi import UploadFile, HTTPException

from ..components.file_manager import FileManager, FileInfo, UploadSession
from ..services.project_service import ProjectService

logger = getLogger(__name__)


class FileService:
    """
    Service for file management operations.
    
    Responsibilities:
    - ZIP file upload and validation
    - File extraction
    - File listing and navigation
    - File content retrieval
    - Folder creation
    """
    
    # Maximum upload size (20MB default)
    MAX_UPLOAD_SIZE = 20 * 1024 * 1024
    
    # Allowed file extensions for analysis
    ALLOWED_EXTENSIONS = ['.py', '.js', '.ts', '.java', '.cpp', '.c', '.h', '.rb', '.go', '.rs']
    
    def __init__(self, file_manager: FileManager, project_service: ProjectService):
        """
        Initialize file service.
        
        Args:
            file_manager: FileManager instance
            project_service: ProjectService instance
        """
        self.file_manager = file_manager
        self.project_service = project_service
        logger.info("FileService initialized")
    
    async def upload_zip(
        self,
        project_id: UUID,
        file: UploadFile,
        max_size: int = MAX_UPLOAD_SIZE
    ) -> UploadSession:
        """
        Upload a ZIP file and extract its contents.
        
        Args:
            project_id: Project UUID
            file: Uploaded ZIP file
            max_size: Maximum file size in bytes
        
        Returns:
            UploadSession with extraction details
        
        Raises:
            HTTPException: If file is invalid or too large
        """
        # Validate project exists
        project = self.project_service.get_by_id(project_id)
        if not project:
            raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")
        
        # Validate file type
        if not file.filename.lower().endswith('.zip'):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Expected .zip, got: {file.filename}"
            )
        
        # Read file content to check size
        content = await file.read()
        file_size = len(content)
        
        if file_size > max_size:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size: {max_size / 1024 / 1024:.1f}MB"
            )
        
        if file_size == 0:
            raise HTTPException(status_code=400, detail="Empty file")
        
        # Create project directory
        project_dir = f"project-{project_id}"
        upload_path = f"{project_dir}/uploads/{file.filename}"
        
        # Save uploaded file
        try:
            # Reset file pointer
            await file.seek(0)
            bytes_written = await self.file_manager.save_uploaded_file(file, upload_path)
            logger.info(f"Saved ZIP file: {upload_path} ({bytes_written} bytes)")
        except Exception as e:
            logger.error(f"Error saving uploaded file: {e}")
            raise HTTPException(status_code=500, detail="Failed to save uploaded file")
        
        # Extract ZIP
        extract_path = f"{project_dir}/source"
        try:
            files_extracted = self.file_manager.extract_zip(upload_path, extract_path)
            logger.info(f"Extracted {files_extracted} files to {extract_path}")
        except zipfile.BadZipFile:
            raise HTTPException(status_code=400, detail="Invalid ZIP file")
        except Exception as e:
            logger.error(f"Error extracting ZIP: {e}")
            raise HTTPException(status_code=500, detail="Failed to extract ZIP file")
        
        # Create upload session
        session = UploadSession(
            session_id=uuid4(),
            project_id=project_id,
            file_count=files_extracted,
            extracted_path=extract_path
        )
        
        logger.info(f"Upload session created: {session.session_id} ({files_extracted} files)")
        return session
    
    def list_files(
        self,
        project_id: UUID,
        path: str = ""
    ) -> List[FileInfo]:
        """
        List files in a project directory.
        
        Args:
            project_id: Project UUID
            path: Subdirectory path (relative to project root)
        
        Returns:
            List of FileInfo objects
        
        Raises:
            HTTPException: If project not found or path invalid
        """
        # Validate project exists
        project = self.project_service.get_by_id(project_id)
        if not project:
            raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")
        
        # Build directory path
        project_dir = f"project-{project_id}/source"
        if path:
            dir_path = f"{project_dir}/{path}"
        else:
            dir_path = project_dir
        
        try:
            files = self.file_manager.list_files(dir_path, project_dir)
            return files
        except NotADirectoryError:
            raise HTTPException(status_code=400, detail=f"Path is not a directory: {path}")
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Error listing files: {e}")
            raise HTTPException(status_code=500, detail="Failed to list files")
    
    def get_file_content(
        self,
        project_id: UUID,
        file_path: str
    ) -> str:
        """
        Get file content.
        
        Args:
            project_id: Project UUID
            file_path: File path relative to project source
        
        Returns:
            File content as string
        
        Raises:
            HTTPException: If file not found or invalid
        """
        # Validate project exists
        project = self.project_service.get_by_id(project_id)
        if not project:
            raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")

        if file_path.startswith("/") or ".." in file_path or "\\" in file_path:
            raise HTTPException(
                status_code=400,
                detail="Invalid file path. Use normalized relative paths such as 'application/app.py'",
            )
        
        # Build file path
        project_dir = f"project-{project_id}/source"
        full_path = f"{project_dir}/{file_path}"
        
        try:
            content = self.file_manager.get_file_content(full_path)
            return content
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
        except IsADirectoryError:
            raise HTTPException(status_code=400, detail="Path is a directory, not a file")
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="File is not a valid text file")
        except Exception as e:
            logger.error(f"Error reading file: {e}")
            raise HTTPException(status_code=500, detail="Failed to read file")
    
    def create_folder(
        self,
        project_id: UUID,
        folder_path: str
    ) -> None:
        """
        Create a folder in the project.
        
        Args:
            project_id: Project UUID
            folder_path: Folder path relative to project source
        
        Raises:
            HTTPException: If folder creation fails
        """
        # Validate project exists
        project = self.project_service.get_by_id(project_id)
        if not project:
            raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")

        if folder_path.startswith("/") or ".." in folder_path or "\\" in folder_path:
            raise HTTPException(
                status_code=400,
                detail="Invalid folder path. Use normalized project-relative paths",
            )
        
        # Build folder path
        project_dir = f"project-{project_id}/source"
        full_path = f"{project_dir}/{folder_path}"
        
        try:
            self.file_manager.create_directory(full_path)
            logger.info(f"Created folder: {folder_path}")
        except FileExistsError:
            raise HTTPException(status_code=400, detail="Folder already exists")
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Error creating folder: {e}")
            raise HTTPException(status_code=500, detail="Failed to create folder")
    
    def discover_source_files(self, project_id: UUID) -> List[str]:
        """
        Discover source files in a project.
        
        Args:
            project_id: Project UUID
        
        Returns:
            List of file paths
        
        Raises:
            HTTPException: If discovery fails
        """
        # Validate project exists
        project = self.project_service.get_by_id(project_id)
        if not project:
            raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")
        
        # Build project path
        project_dir = f"project-{project_id}/source"
        
        try:
            discovered_files = self.file_manager.discover_files(
                project_dir,
                extensions=self.ALLOWED_EXTENSIONS
            )
            prefix = f"{project_dir}/"
            files = [
                file_path[len(prefix):] if file_path.startswith(prefix) else file_path
                for file_path in discovered_files
            ]
            logger.info(f"Discovered {len(files)} source files in project {project_id}")
            return files
        except Exception as e:
            logger.error(f"Error discovering files: {e}")
            raise HTTPException(status_code=500, detail="Failed to discover source files")
