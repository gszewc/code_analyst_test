"""Analysis orchestrator for background analysis tasks."""

import asyncio
from logging import getLogger
from pathlib import Path
from typing import List, Optional
from uuid import UUID

from ..parsing.registry import ParserRegistry
from ..parsing.discovery import FileDiscovery
from ..parsing.models import ASTResult, CrossFileConfig
from ..database.graph_storage import GraphStorage
from ..database.project_storage import ProjectStorage
from ..database.analysis_storage import AnalysisStorage

logger = getLogger(__name__)


class AnalysisOrchestrator:
    """
    Orchestrates background analysis tasks.

    Responsibilities:
    - Per-language sequential file processing via ParserRegistry
    - AST parsing and result storage
    - Progress tracking
    - Error handling (skip unparsable files)
    - Optional repository map generation
    """

    def __init__(
        self,
        parser_registry: ParserRegistry,
        file_discovery: FileDiscovery,
        graph_storage: GraphStorage,
        project_storage: ProjectStorage,
        analysis_storage: AnalysisStorage,
        repo_map_generator=None,
    ):
        self.parser_registry = parser_registry
        self.file_discovery = file_discovery
        self.graph_storage = graph_storage
        self.project_storage = project_storage
        self.analysis_storage = analysis_storage
        self.repo_map_generator = repo_map_generator
        logger.info("AnalysisOrchestrator initialized")

    async def _parse_project(
        self,
        project_path: str,
        project_source_root: str | None = None,
        cross_file_config: CrossFileConfig | None = None,
        enabled_node_types: list[str] | None = None,
        enabled_relationship_types: list[str] | None = None,
        languages: list[str] | None = None,
        folders: list[str] | None = None,
    ) -> tuple[list[ASTResult], int]:
        """Discover and parse project files per language.

        Returns:
            (results, total_file_count) — one ASTResult per language,
            filtered if enabled_node/relationship_types given.
        """
        files_by_language = self.file_discovery.discover_files(
            project_path, languages, folders
        )
        if not files_by_language:
            raise RuntimeError("No source files found for any registered language")

        normalization_root = project_source_root or project_path
        results: list[ASTResult] = []
        total_files = 0

        for language, lang_files in files_by_language.items():
            parser = self.parser_registry.get_parser_for_language(language)
            if parser is None:
                continue

            result = await asyncio.to_thread(
                parser.parse_files, lang_files, normalization_root
            )
            if result is None:
                continue

            if result.nodes:
                resolver = parser.create_cross_file_resolver()
                if resolver:
                    config = cross_file_config or CrossFileConfig()
                    new_rels, new_nodes = resolver.resolve(result, config)
                    result.nodes.extend(new_nodes)
                    result.relationships.extend(new_rels)

            if enabled_node_types is not None or enabled_relationship_types is not None:
                result = self.filter_ast_result(
                    result,
                    enabled_node_types=enabled_node_types,
                    enabled_relationship_types=enabled_relationship_types,
                )

            results.append(result)
            total_files += len(lang_files)

        return results, total_files

    async def orchestrate_analysis_for_directory(
        self,
        project_id: UUID,
        job_id: UUID,
        project_path: str,
        file_paths: list[str] | None = None,  # kept for backward compat
        project_source_root: str | None = None,
        cross_file_config: CrossFileConfig | None = None,
        delete_graph_data: bool = False,
        enabled_node_types: list[str] | None = None,
        enabled_relationship_types: list[str] | None = None,
        languages: list[str] | None = None,
        folders: list[str] | None = None,
        generate_map: bool = False,
    ) -> None:
        """Orchestrate full analysis: parse → store graph → optionally generate map."""
        self.analysis_storage.start_job(str(job_id))
        try:
            if delete_graph_data:
                logger.info(f"Deleting graph data for project {project_id}")
                self.graph_storage.delete_by_project(str(project_id))

            results, total_files = await self._parse_project(
                project_path=project_path,
                project_source_root=project_source_root,
                cross_file_config=cross_file_config,
                enabled_node_types=enabled_node_types,
                enabled_relationship_types=enabled_relationship_types,
                languages=languages,
                folders=folders,
            )

            total_nodes = 0
            total_errors = 0
            all_map_nodes = []

            for result in results:
                if result.nodes:
                    self.graph_storage.store_ast_result(str(project_id), result)
                if generate_map:
                    all_map_nodes.extend(result.nodes)
                total_nodes += len(result.nodes)
                total_errors += len(result.errors)

            if generate_map and self.repo_map_generator is not None:
                norm_root = project_source_root or project_path
                map_output = Path(norm_root) / "repomap.txt"
                self.repo_map_generator.generate(all_map_nodes, map_output)

            await self._update_progress(job_id, total_files, total_files, project_path)
            self.analysis_storage.complete_job(str(job_id), total_files)
            logger.info(
                f"Analysis complete for job {job_id}: {total_files} files, {total_nodes} nodes"
            )
        except Exception as e:
            logger.error(f"Error in analysis for {project_path}: {e}", exc_info=True)
            self.analysis_storage.fail_job(str(job_id), str(e))
            raise

    async def generate_map_for_directory(
        self,
        project_path: str,
        output_path: Path,
        project_source_root: str | None = None,
        cross_file_config: CrossFileConfig | None = None,
        languages: list[str] | None = None,
        folders: list[str] | None = None,
    ) -> None:
        """Parse project files and generate repository map without graph storage."""
        if self.repo_map_generator is None:
            logger.warning("RepoMapGenerator not injected, skipping map generation")
            return

        results, _ = await self._parse_project(
            project_path=project_path,
            project_source_root=project_source_root,
            cross_file_config=cross_file_config,
            languages=languages,
            folders=folders,
        )

        all_nodes = [node for result in results for node in result.nodes]
        self.repo_map_generator.generate(all_nodes, output_path)

    @staticmethod
    def filter_ast_result(
        result: ASTResult,
        enabled_node_types: Optional[List[str]] = None,
        enabled_relationship_types: Optional[List[str]] = None,
    ) -> ASTResult:
        """Filter AST result to only include enabled node and relationship types."""
        if enabled_node_types is not None:
            enabled_set = set(enabled_node_types)
            filtered_nodes = [n for n in result.nodes if n.type in enabled_set]
        else:
            filtered_nodes = list(result.nodes)

        surviving_ids = {n.id for n in filtered_nodes}

        if enabled_relationship_types is not None:
            rel_set = set(enabled_relationship_types)
            filtered_rels = [
                r
                for r in result.relationships
                if r.type in rel_set
                and r.source_id in surviving_ids
                and r.target_id in surviving_ids
            ]
        else:
            filtered_rels = [
                r
                for r in result.relationships
                if r.source_id in surviving_ids and r.target_id in surviving_ids
            ]

        return ASTResult(
            file_info=result.file_info,
            nodes=filtered_nodes,
            relationships=filtered_rels,
            errors=result.errors,
            summary=result.summary,
            raw_imports=result.raw_imports,
            unresolved_references=result.unresolved_references,
        )

    async def _update_progress(
        self,
        job_id: UUID,
        processed: int,
        total: int,
        current_file: Optional[str] = None,
    ) -> None:
        try:
            self.analysis_storage.update_progress(
                job_id=str(job_id), files_count=processed
            )
            logger.debug(f"Job {job_id} progress: {processed}/{total}")
        except Exception as e:
            logger.error(f"Error updating progress for job {job_id}: {e}")
