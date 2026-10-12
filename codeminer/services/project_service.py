"""Project service for project CRUD operations."""

import re
from datetime import datetime
from logging import getLogger
from typing import List, Optional
from uuid import UUID

from ..database.project_storage import ProjectStorage, ProjectNotFoundError, ProjectConflictError, ProjectValidationError
from ..database.models import Project as ProjectModel

logger = getLogger(__name__)


class ProjectService:
    """
    Service for project management operations.
    
    Business Rules:
    - Project names must be alphanumeric with hyphens/underscores
    - Project names must be unique (case-sensitive)
    - Projects are hard-deleted
    - Projects cannot be deleted if they have running analysis jobs
    """
    
    def __init__(self, project_storage: ProjectStorage):
        """
        Initialize project service.
        
        Args:
            project_storage: ProjectStorage instance
        """
        self.project_storage = project_storage
        logger.info("ProjectService initialized")
    
    def create(self, name: str, description: Optional[str] = None) -> ProjectModel:
        """
        Create a new project.
        
        Args:
            name: Project name
            description: Optional project description
        
        Returns:
            Created Project
        
        Raises:
            ValueError: If name is invalid or duplicate
        """
        try:
            project = self.project_storage.create_project(name, description or '')
            logger.info(f"Created project: {project.id} - {name}")
            return project
        except ProjectValidationError as e:
            logger.warning(f"Project validation failed: {e}")
            raise ValueError(str(e))
        except ProjectConflictError as e:
            logger.warning(f"Project conflict: {e}")
            raise ValueError(str(e))
    
    def list_all(self) -> List[ProjectModel]:
        """
        List all projects.
        
        Returns:
            List of Project objects
        """
        projects = self.project_storage.list_projects(limit=1000)
        logger.debug(f"Listed {len(projects)} projects")
        return projects
    
    def get_by_id(self, project_id: UUID) -> Optional[ProjectModel]:
        """
        Get project by ID.
        
        Args:
            project_id: Project UUID
        
        Returns:
            Project or None if not found
        """
        try:
            project = self.project_storage.get_project(str(project_id))
            if not project:
                logger.debug(f"Project not found: {project_id}")
            return project
        except Exception as e:
            logger.error(f"Error getting project: {e}")
            return None
    
    def update(
        self,
        project_id: UUID,
        name: Optional[str] = None,
        description: Optional[str] = None
    ) -> Optional[ProjectModel]:
        """
        Update project.
        
        Args:
            project_id: Project UUID
            name: New name (optional)
            description: New description (optional)
        
        Returns:
            Updated Project or None if not found
        
        Raises:
            ValueError: If name is invalid or duplicate
        """
        try:
            project = self.project_storage.update_project(
                str(project_id),
                name=name,
                description=description
            )
            logger.info(f"Updated project: {project_id}")
            return project
        except ProjectNotFoundError:
            logger.debug(f"Project not found: {project_id}")
            return None
        except ProjectValidationError as e:
            logger.warning(f"Project validation failed: {e}")
            raise ValueError(str(e))
        except ProjectConflictError as e:
            logger.warning(f"Project conflict: {e}")
            raise ValueError(str(e))
    
    def delete(self, project_id: UUID) -> None:
        """
        Delete a project.
        
        Args:
            project_id: Project UUID
        
        Raises:
            ValueError: If project not found or has running analysis
        """
        from ..database.analysis_storage import AnalysisStorage
        from ..container import get_container
        
        # Check for running analysis jobs
        try:
            container = get_container()
            analysis_storage = container.get(AnalysisStorage)
            running_jobs = analysis_storage.get_running_jobs(str(project_id))
            if running_jobs:
                logger.warning(f"Cannot delete project {project_id}: {len(running_jobs)} running jobs")
                raise ValueError(f"Cannot delete project with {len(running_jobs)} running analysis job(s)")
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error checking running jobs: {e}")
        
        try:
            self.project_storage.delete_project(str(project_id))
            logger.info(f"Deleted project: {project_id}")
        except ProjectNotFoundError:
            logger.warning(f"Project not found for deletion: {project_id}")
            raise ValueError(f"Project not found: {project_id}")
        except Exception as e:
            logger.error(f"Error deleting project: {e}")
            raise
