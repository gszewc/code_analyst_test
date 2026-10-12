"""Project API routes."""

from logging import getLogger
from fastapi import APIRouter, HTTPException, Depends
import fastapi.exceptions
from uuid import UUID
import re


from ...models.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectListResponse,
)
from ...services.project_service import ProjectService
from ... import container

logger = getLogger(__name__)

router = APIRouter(prefix="/projects", tags=["Projects"])

# Validation patterns
NAME_PATTERN = re.compile(r'^[a-zA-Z0-9_ -]+$')
MAX_NAME_LENGTH = 255
MAX_DESCRIPTION_LENGTH = 1000

def get_project_service() -> ProjectService:
    """Get project service from container."""
    return container.get_container().get(ProjectService)

def _validate_project_name( name: str) -> None:
        """Validate project name.

        Args:
            name: Project name to validate

        Raises:
            ProjectValidationError: If name is invalid
        """
        logger.debug(f"Validating project name: {name}")
        if not name or not name.strip():
            raise HTTPException(status_code=422, detail='Project name is required')

        if len(name) > MAX_NAME_LENGTH:
            raise HTTPException(
                status_code=422,
                detail=f'Project name must be <= {MAX_NAME_LENGTH} characters'
            )

        if not NAME_PATTERN.match(name):
            raise HTTPException(
                status_code=422, detail='Invalid project name format'
                 'Project name must contain only alphanumeric characters, '
                 'spaces, hyphens, and underscores'
            )

@router.post("/", response_model=ProjectResponse, status_code=201)
async def create_project(
    project: ProjectCreate, service: ProjectService = Depends(get_project_service)
):
    """
    Create a new project.

    - **name**: Project name (required, 1-255 chars, alphanumeric with hyphens/underscores)
    - **description**: Project description (optional, max 1000 chars)
    """
    try:
        logger.debug(f"Creating project with name: {project.name}")
        _validate_project_name(project.name)

        created = service.create(project.name, project.description)
        logger.info(f"Created project: {created.id}")
        return created
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=ProjectListResponse)
async def list_projects(service: ProjectService = Depends(get_project_service)):
    """
    List all projects.

    Returns all non-deleted projects.
    """
    projects = service.list_all()
    return ProjectListResponse(projects=projects, total=len(projects))


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID, service: ProjectService = Depends(get_project_service)
):
    """
    Get project by ID.exceptions
    """
    project = service.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")
    return project


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    project_update: ProjectUpdate,
    service: ProjectService = Depends(get_project_service),
):
    """
    Update project.

    - **name**: New project name (optional)
    - **description**: New description (optional)
    """
    try:
        updated = service.update(project_id, project_update.name, project_update.description)
        if not updated:
            raise HTTPException(
                status_code=404, detail=f"Project not found: {project_id}"
            )
        logger.info(f"Updated project: {project_id}")
        return updated
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: UUID, service: ProjectService = Depends(get_project_service)
):
    """
    Delete project (soft delete).

    Marks the project as deleted. Projects with running analysis jobs cannot be deleted.
    """
    try:
        service.delete(project_id)
        logger.info(f"Deleted project: {project_id}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
