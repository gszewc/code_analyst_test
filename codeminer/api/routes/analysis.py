"""Analysis API routes."""

from logging import getLogger
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from uuid import UUID

from ...config import get_settings
from ...models.analysis import (
    AnalysisJobResponse,
    AnalysisJobListResponse,
    AnalysisStartRequest,
    AnalysisDefaultsResponse,
)
from ...database.models import GraphSummary
from ...services.analysis_service import AnalysisService
from ...services.graph_service import GraphService
from ...parsing.registry import ParserRegistry
from ... import container

logger = getLogger(__name__)

router = APIRouter(prefix="/analysis", tags=["Analysis"])


def get_analysis_service() -> AnalysisService:
    """Get analysis service from container."""
    return container.get_container().get(AnalysisService)


def get_graph_service() -> GraphService:
    """Get graph service from container."""
    return container.get_container().get(GraphService)


def get_parser_registry() -> ParserRegistry:
    """Get parser registry from container."""
    return container.get_container().get(ParserRegistry)


@router.get("/defaults", response_model=AnalysisDefaultsResponse)
async def get_analysis_defaults(
    registry: ParserRegistry = Depends(get_parser_registry),
):
    """Return default analysis configuration."""
    settings = get_settings()
    defaults = settings.analysis_defaults
    return AnalysisDefaultsResponse(
        delete_graph_data=defaults.delete_graph_data,
        enabled_node_types=defaults.enabled_node_types,
        enabled_relationship_types=defaults.enabled_relationship_types,
        languages=registry.get_supported_languages(),
    )


@router.get(
    "/projects/{project_id}/graph-summary",
    response_model=GraphSummary,
)
async def get_graph_summary(
    project_id: UUID,
    service: GraphService = Depends(get_graph_service),
):
    """Return graph data summary for deletion confirmation."""
    try:
        return service.get_graph_summary(str(project_id))
    except Exception as e:
        logger.error(f"Error getting graph summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to get graph summary")


@router.post(
    "/projects/{project_id}/analyze",
    response_model=AnalysisJobResponse,
    status_code=201,
)
async def start_analysis(
    project_id: UUID,
    background_tasks: BackgroundTasks,
    body: Optional[AnalysisStartRequest] = None,
    service: AnalysisService = Depends(get_analysis_service),
):
    """Start analysis for a project."""
    try:
        job = service.create_job(project_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        # Extract config from request body
        cross_file_config = body.cross_file_relations if body else None
        languages = body.languages if body else None
        folders = body.folders if body else None
        generate_map = body.generate_map if body is not None else True

        # Resolve analysis options (None = use defaults from settings)
        settings = get_settings()
        defaults = settings.analysis_defaults
        delete_graph_data = (
            body.delete_graph_data if body and body.delete_graph_data is not None
            else defaults.delete_graph_data
        )
        enabled_node_types = (
            [t.value for t in body.enabled_node_types] if body and body.enabled_node_types is not None
            else defaults.enabled_node_types
        )
        enabled_relationship_types = (
            [t.value for t in body.enabled_relationship_types] if body and body.enabled_relationship_types is not None
            else defaults.enabled_relationship_types
        )

        # Validate at least one type selected
        if not enabled_node_types:
            raise ValueError("At least one node type must be selected")
        if not enabled_relationship_types:
            raise ValueError("At least one relationship type must be selected")

        background_tasks.add_task(
            service.run_analysis,
            job.id,
            cross_file_config,
            delete_graph_data,
            enabled_node_types,
            enabled_relationship_types,
            languages,
            folders,
            generate_map,
        )

        logger.info(f"Started analysis job: {job.id} for project {project_id}")
        return AnalysisJobResponse(
            id=job.id,
            project_id=job.project_id,
            status=job.status,
            progress=0,
            error_message=job.error_message,
            started_at=job.started_at,
            completed_at=job.completed_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Error starting analysis: {e}")
        raise HTTPException(status_code=500, detail="Failed to start analysis")


@router.get("/jobs/{job_id}", response_model=AnalysisJobResponse)
async def get_analysis_job(
    job_id: UUID, service: AnalysisService = Depends(get_analysis_service)
):
    """
    Get analysis job status.

    - **job_id**: Job UUID

    Returns job status and progress information.
    """
    job = service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    return AnalysisJobResponse(
        id=job.id,
        project_id=job.project_id,
        status=job.status,
        progress=0, #job.progress,
        error_message=job.error_message,
        started_at=job.started_at,
        completed_at=job.completed_at,
        #created_at=job.created_at,
    )


@router.get("/projects/{project_id}/jobs", response_model=AnalysisJobListResponse)
async def list_analysis_jobs(
    project_id: UUID, service: AnalysisService = Depends(get_analysis_service)
):
    """
    List analysis jobs for a project.

    - **project_id**: Project UUID

    Returns all analysis jobs for the project.
    """
    jobs = service.get_jobs_by_project(project_id)
    return AnalysisJobListResponse(
        jobs=[
            AnalysisJobResponse(
                id=job.id,
                project_id=job.project_id,
                status=job.status,
                progress=0, #job.progress,
                error_message=job.error_message,
                started_at=job.started_at,
                completed_at=job.completed_at,
                #created_at=job.created_at,
            )
            for job in jobs
        ],
        total=len(jobs),
    )


@router.post(
    "/projects/{project_id}/generate-map",
    status_code=200,
)
async def generate_project_map(
    project_id: UUID,
    service: AnalysisService = Depends(get_analysis_service),
):
    """Generate repository map for a project from its source files.

    Parses source files without storing to the graph database.
    Writes repomap.txt to the project source root.
    """
    try:
        await service.generate_map_for_project(project_id)
        return {"status": "ok", "path": "repomap.txt"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating map for project {project_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate repository map")
