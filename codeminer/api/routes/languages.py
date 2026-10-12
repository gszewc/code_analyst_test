"""Language-related API routes."""

from logging import getLogger
from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID
import os

from ...parsing.registry import ParserRegistry
from ...parsing.discovery import FileDiscovery
from ...services.project_service import ProjectService
from ...components.file_manager import FileManager
from ... import container

logger = getLogger(__name__)

router = APIRouter(prefix="/languages", tags=["Languages"])


def get_parser_registry() -> ParserRegistry:
    return container.get_container().get(ParserRegistry)


def get_file_discovery() -> FileDiscovery:
    return container.get_container().get(FileDiscovery)


def get_file_manager() -> FileManager:
    return container.get_container().get(FileManager)


def get_project_service() -> ProjectService:
    return container.get_container().get(ProjectService)


@router.get("")
async def get_languages(registry: ParserRegistry = Depends(get_parser_registry)):
    """Return all registered languages with their type definitions."""
    languages = []
    for lang_name in registry.get_supported_languages():
        parser = registry.get_parser_for_language(lang_name)
        if parser is None:
            continue
        languages.append({
            "name": lang_name,
            "extensions": parser.get_supported_extensions(),
            "node_types": [d.model_dump() for d in parser.get_node_type_definitions()],
            "relationship_types": [d.model_dump() for d in parser.get_relationship_type_definitions()],
        })
    return {"languages": languages}


@router.get("/projects/{project_id}/detected-languages")
async def get_detected_languages(
    project_id: UUID,
    discovery: FileDiscovery = Depends(get_file_discovery),
    file_manager: FileManager = Depends(get_file_manager),
    project_service: ProjectService = Depends(get_project_service),
):
    """Detect languages present in a project's uploaded files."""
    project = project_service.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    project_path = file_manager.get_safe_path(f"project-{project_id}/source")
    if not os.path.isdir(project_path):
        return {"languages": []}

    files_by_lang = discovery.discover_files(str(project_path))

    languages = []
    for lang_name, files in files_by_lang.items():
        folders = set()
        for f in files:
            rel = os.path.relpath(f, project_path)
            parts = rel.split(os.sep)
            if len(parts) > 1:
                folders.add(parts[0] + "/")
            else:
                folders.add("./")
        languages.append({
            "name": lang_name,
            "file_count": len(files),
            "folders": sorted(folders),
        })

    return {"languages": languages}
