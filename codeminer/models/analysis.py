"""Analysis job data models."""

from datetime import datetime
from uuid import UUID, uuid4
from typing import Optional, List
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict

from codeminer.parsing.models import CrossFileConfig, NodeType, RelationshipType


class AnalysisStatus(str, Enum):
    """Analysis job status enumeration."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AnalysisProgress(BaseModel):
    """Analysis progress information."""

    processed: int = Field(..., description="Number of files processed")
    total: int = Field(..., description="Total number of files to process")
    current_file: Optional[str] = Field(None, description="Currently processing file")
    percentage: float = Field(..., description="Completion percentage")

    @classmethod
    def create(
        cls, processed: int, total: int, current_file: Optional[str] = None
    ) -> "AnalysisProgress":
        """Create progress with calculated percentage."""
        percentage = (processed / total * 100) if total > 0 else 0.0
        return cls(
            processed=processed,
            total=total,
            current_file=current_file,
            percentage=percentage,
        )


class AnalysisJobBase(BaseModel):
    """Base analysis job model."""

    project_id: UUID = Field(..., description="Project ID")


class AnalysisJobCreate(AnalysisJobBase):
    """Request model for creating an analysis job."""

    pass


class AnalysisJob(AnalysisJobBase):
    """Analysis job domain model."""

    id: UUID = Field(default_factory=uuid4, description="Job ID")
    status: AnalysisStatus = Field(
        default=AnalysisStatus.PENDING, description="Job status"
    )
    progress: Optional[AnalysisProgress] = Field(
        None, description="Progress information"
    )
    error_message: Optional[str] = Field(None, description="Error message if failed")
    started_at: Optional[datetime] = Field(None, description="Start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    # created_at: datetime = Field(
    #     default_factory=datetime.utcnow, description="Creation timestamp"
    # )

    model_config = ConfigDict(from_attributes=True)


class AnalysisJobResponse(BaseModel):
    """Response model for an analysis job."""
    """
Attributes:
        id: Analysis UUID
        project_id: Reference to parent project
        started_at: Analysis start time
        completed_at: Completion time (None if in progress)
        files_count: Number of files processed
        nodes_count: Number of nodes stored
        relationships_count: Number of relationships stored
        status: Analysis status (pending|running|completed|failed)
        error_message: Error message if failed
    """


    id: UUID
    project_id: UUID
    status: AnalysisStatus
    # progress: Optional[AnalysisProgress]
    # For simplicity, we return progress as an integer percentage in the API response
    progress: Optional[int]
    error_message: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    #created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AnalysisJobListResponse(BaseModel):
    """Response model for listing analysis jobs."""

    jobs: list[AnalysisJobResponse] = Field(
        default_factory=list, description="List of jobs"
    )
    total: int = Field(..., description="Total number of jobs")


class AnalysisDefaultsResponse(BaseModel):
    """Response model for analysis defaults endpoint."""

    delete_graph_data: bool
    enabled_node_types: List[NodeType]
    enabled_relationship_types: List[RelationshipType]
    languages: List[str]


class AnalysisStartRequest(BaseModel):
    """Request body for starting analysis."""

    cross_file_relations: Optional[CrossFileConfig] = None
    delete_graph_data: Optional[bool] = None
    enabled_node_types: Optional[List[NodeType]] = None
    enabled_relationship_types: Optional[List[RelationshipType]] = None
    languages: Optional[List[str]] = None
    folders: Optional[List[str]] = None
    generate_map: bool = True
