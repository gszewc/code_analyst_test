"""File API routes."""

from logging import getLogger
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query
from uuid import UUID

import inspect

from ...services.file_service import FileService
from ... import container

logger = getLogger(__name__)

router = APIRouter(prefix="/projects", tags=["Files"])


def get_file_service() -> FileService:
    """Get file service from container."""
    return container.get_container().get(FileService)


@router.post("/{project_id}/upload", status_code=201)
async def upload_zip(
    project_id: UUID,
    file: UploadFile = File(..., description="ZIP file to upload"),
    service: FileService = Depends(get_file_service),
):
    """
    Upload a ZIP file and extract its contents.

    - **project_id**: Project UUID
    - **file**: ZIP file containing source code

    Returns upload session with file count and extraction path.
    """
    try:
        session = service.upload_zip(project_id, file)
        if inspect.isawaitable(session):
            session = await session
        logger.info(f"Upload session created: {session.session_id}")
        return {
            "session_id": str(session.session_id),
            "project_id": str(session.project_id),
            "file_count": session.file_count,
            "extracted_path": session.extracted_path,
        }
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail="Upload failed")


@router.get("/{project_id}/files")
async def list_files(
    project_id: UUID,
    path: str = Query(default="", description="Subdirectory path"),
    service: FileService = Depends(get_file_service),
):
    """
    List files in a project directory.

    - **project_id**: Project UUID
    - **path**: Subdirectory path (optional, defaults to project root)

    Returns list of files and directories.
    """
    try:
        files = service.list_files(project_id, path)
        return {"files": [f.to_dict() for f in files], "total": len(files)}
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{project_id}/files/{filepath:path}")
async def get_file_content(
    project_id: UUID, filepath: str, service: FileService = Depends(get_file_service)
):
    """
    Get file content.

    - **project_id**: Project UUID
    - **filepath**: File path relative to project source

    Returns file content as plain text.
    """
    try:
        content = service.get_file_content(project_id, filepath)
        return {"content": content}
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{project_id}/folders", status_code=201)
async def create_folder(
    project_id: UUID,
    folder_path: str = Query(..., description="Folder path to create"),
    service: FileService = Depends(get_file_service),
):
    """
    Create a folder in the project.

    - **project_id**: Project UUID
    - **folder_path**: Folder path relative to project source
    """
    try:
        service.create_folder(project_id, folder_path)
        return {"message": f"Folder created: {folder_path}"}
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
