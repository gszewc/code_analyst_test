"""Abstract base classes for language parsers."""

from abc import ABC, abstractmethod
from typing import Optional

from .models import ASTResult, ASTNode, Relationship, CrossFileConfig
from .types import NodeTypeDefinition, RelationshipTypeDefinition


class CrossFileResolverBase(ABC):
    """Abstract base for cross-file relationship resolution."""

    @abstractmethod
    def resolve(
        self,
        ast_result: ASTResult,
        config: Optional[CrossFileConfig] = None,
    ) -> tuple[list[Relationship], list[ASTNode]]:
        """Resolve cross-file relationships within a single language.

        Args:
            ast_result: Combined ASTResult for all files of one language.
            config: Optional cross-file config flags.

        Returns:
            Tuple of (new_relationships, new_nodes).
        """


class LanguageParser(ABC):
    """Abstract base class for language parsers."""

    @abstractmethod
    def get_language_name(self) -> str:
        """Return language identifier, e.g. 'python', 'java'."""

    @abstractmethod
    def get_supported_extensions(self) -> list[str]:
        """Return file extensions, e.g. ['.py'] or ['.cpp', '.cc']."""

    @abstractmethod
    def get_node_type_definitions(self) -> list[NodeTypeDefinition]:
        """Return node types with metadata for frontend display."""

    @abstractmethod
    def get_relationship_type_definitions(self) -> list[RelationshipTypeDefinition]:
        """Return relationship types with metadata for frontend display."""

    @abstractmethod
    def get_excluded_dirs(self) -> set[str]:
        """Return language-specific directories to exclude from discovery."""

    @abstractmethod
    def parse_file(self, file_path: str, project_root: Optional[str] = None) -> ASTResult:
        """Parse a single file."""

    @abstractmethod
    def parse_files(self, file_paths: list[str], project_root: Optional[str] = None) -> ASTResult:
        """Parse multiple files. Errors collected in ASTResult.errors."""

    @abstractmethod
    def create_cross_file_resolver(self) -> Optional[CrossFileResolverBase]:
        """Return a cross-file resolver for this language, or None."""
