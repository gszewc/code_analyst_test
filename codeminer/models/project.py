"""Project data models."""

from datetime import datetime
from uuid import UUID, uuid4
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

from ..datetime_utils import utc_now


class ProjectBase(BaseModel):
    """Base project model with common fields."""

    name: str = Field(..., min_length=1, max_length=255, description="Project name")
    description: Optional[str] = Field(
        None, max_length=1000, description="Project description"
    )


class ProjectCreate(ProjectBase):
    """Request model for creating a project."""

    pass


class ProjectUpdate(BaseModel):
    """Request model for updating a project."""

    name: Optional[str] = Field(
        None, min_length=1, max_length=255, description="Project name"
    )
    description: Optional[str] = Field(
        None, max_length=1000, description="Project description"
    )


class Project(ProjectBase):
    """Project domain model."""

    id: UUID = Field(default_factory=uuid4, description="Project ID")
    created_at: datetime = Field(
        default_factory=utc_now, description="Creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=utc_now, description="Last update timestamp"
    )
    is_deleted: bool = Field(default=False, description="Soft delete flag")
    model_config = ConfigDict(from_attributes=True)


class ProjectResponse(Project):
    """Response model for a single project."""

    pass


class ProjectListResponse(BaseModel):
    """Response model for listing projects."""

    projects: list[Project] = Field(
        default_factory=list, description="List of projects"
    )
    total: int = Field(..., description="Total number of projects")
