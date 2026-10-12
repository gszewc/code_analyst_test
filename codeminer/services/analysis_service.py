"""Analysis service for analysis job management and orchestration."""
from logging import getLogger
from typing import List, Optional
from uuid import UUID

from ..parsing.registry import ParserRegistry
from ..parsing.discovery import FileDiscovery
from ..components.file_manager import FileManager
from ..components.analysis_orchestrator import AnalysisOrchestrator
from ..database.graph_storage import GraphStorage
from ..database.project_storage import ProjectStorage
from ..database.analysis_storage import AnalysisStorage
from ..database.models import Analysis

logger = getLogger(__name__)


class AnalysisService:
    """
    Service for analysis job management.
    
    Responsibilities:
    - Create and manage analysis jobs
    - Orchestrate background analysis tasks
    - Track analysis progress
    - Enforce single analysis per project constraint
    """
    
    def __init__(
        self,
        project_storage: ProjectStorage,
        analysis_storage: AnalysisStorage,
        graph_storage: GraphStorage,
        file_manager: FileManager,
        parser_registry: ParserRegistry,
        file_discovery: FileDiscovery,
        orchestrator: Optional[AnalysisOrchestrator] = None,
    ):
        """
        Initialize analysis service.

        Args:
            project_storage: ProjectStorage for project data
            analysis_storage: AnalysisStorage for job tracking
            graph_storage: GraphStorage for graph storage
            file_manager: FileManager for path resolution
            parser_registry: ParserRegistry for language parsers
            file_discovery: FileDiscovery for file discovery
            orchestrator: Optional pre-configured AnalysisOrchestrator; created if not provided
        """
        self.project_storage = project_storage
        self.analysis_storage = analysis_storage
        self.graph_storage = graph_storage
        self.file_manager = file_manager
        self.parser_registry = parser_registry
        self.file_discovery = file_discovery

        self.orchestrator = orchestrator or AnalysisOrchestrator(
            parser_registry=parser_registry,
            file_discovery=file_discovery,
            graph_storage=graph_storage,
            project_storage=project_storage,
            analysis_storage=analysis_storage,
        )
        
        logger.info("AnalysisService initialized")
    
    def create_job(self, project_id: UUID) -> Analysis:
        """
        Create a new analysis job.
        
        Args:
            project_id: Project UUID
        
        Returns:
            Created Analysis job
        
        Raises:
            ValueError: If project already has a running analysis
        """
        # Check for running job
        running_jobs = self.analysis_storage.get_running_jobs(str(project_id))
        if running_jobs:
            logger.warning(f"Project {project_id} already has running analysis")
            raise ValueError(f"Analysis already running for project {project_id}")
        
        # Create job
        job = self.analysis_storage.create_job(str(project_id), 'pending')
        logger.info(f"Created analysis job: {job.id} for project {project_id}")
        
        return job
    
    def get_job(self, job_id: UUID) -> Optional[Analysis]:
        """
        Get analysis job by ID.
        
        Args:
            job_id: Job UUID
        
        Returns:
            Analysis or None if not found
        """
        job = self.analysis_storage.get_job(str(job_id))
        if not job:
            logger.debug(f"Analysis job not found: {job_id}")
        return job
    
    def get_jobs_by_project(self, project_id: UUID) -> List[Analysis]:
        """
        Get all analysis jobs for a project.
        
        Args:
            project_id: Project UUID
        
        Returns:
            List of Analysis jobs
        """
        jobs = self.analysis_storage.get_jobs_by_project(str(project_id))
        logger.debug(f"Retrieved {len(jobs)} jobs for project {project_id}")
        return jobs
    
    async def run_analysis(
        self,
        job_id: UUID,
        cross_file_config=None,
        delete_graph_data=False,
        enabled_node_types=None,
        enabled_relationship_types=None,
        languages=None,
        folders=None,
        generate_map: bool = True,
    ) -> None:
        """
        Run analysis for a job (background task).

        Args:
            job_id: Job UUID
            cross_file_config: Optional cross-file relationship detection config
            delete_graph_data: Whether to delete existing graph data before analysis
            enabled_node_types: List of node type strings to include in analysis
            enabled_relationship_types: List of relationship type strings to include in analysis
            languages: Optional list of language identifiers to restrict parsing
            folders: Optional list of folder paths to restrict discovery

        Raises:
            ValueError: If job not found
        """
        job = self.get_job(job_id)
        if not job:
            raise ValueError(f"Analysis job not found: {job_id}")

        project_id = job.project_id

        try:
            # Build project path
            project_path = f"project-{project_id}/source"
            project_path = self.file_manager.get_safe_path(project_path)
            # Run orchestration (file discovery handled internally by orchestrator)
            await self.orchestrator.orchestrate_analysis_for_directory(
                project_id=UUID(project_id),
                job_id=job_id,
                project_path=project_path,
                project_source_root=str(project_path),
                cross_file_config=cross_file_config,
                delete_graph_data=delete_graph_data,
                enabled_node_types=enabled_node_types,
                enabled_relationship_types=enabled_relationship_types,
                languages=languages,
                folders=folders,
                generate_map=generate_map,
            )

            
        except Exception as e:
            logger.error(f"Analysis failed for job {job_id}: {e}", exc_info=True)
            self.analysis_storage.fail_job(str(job_id), f"Analysis failed: {e}")

    async def generate_map_for_project(
        self,
        project_id: UUID,
        languages: list[str] | None = None,
        folders: list[str] | None = None,
    ) -> None:
        """Generate repository map for a project without running full analysis.

        Args:
            project_id: Project UUID
            languages: Optional language filter
            folders: Optional folder filter

        Raises:
            ValueError: If project does not exist
            FileNotFoundError: If project has no uploaded source files
        """
        project = self.project_storage.get_project(str(project_id))
        if not project:
            raise ValueError(f"Project not found: {project_id}")

        project_path = self.file_manager.get_safe_path(f"project-{project_id}/source")
        if not project_path.exists():
            raise FileNotFoundError(f"No source files found for project {project_id}")

        output_path = project_path / "repomap.txt"
        await self.orchestrator.generate_map_for_directory(
            project_path=str(project_path),
            output_path=output_path,
            project_source_root=str(project_path),
            languages=languages,
            folders=folders,
        )

