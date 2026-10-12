"""
Data models for AST Parser.

This module defines pydantic models for representing parsed AST structures,
including nodes, relationships, errors, and summary statistics.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from datetime import datetime
from enum import Enum


class NodeType(str, Enum):
    """Types of AST nodes."""
    FILE = "File"
    MODULE = "Module"
    PACKAGE = "Package"
    CLASS = "Class"
    INTERFACE = "Interface"
    ENUM = "Enum"
    FUNCTION = "Function"
    METHOD = "Method"
    CONSTRUCTOR = "Constructor"
    VARIABLE = "Variable"
    IMPORT = "Import"
    EXTERNAL_MODULE = "ExternalModule"


class RelationshipType(str, Enum):
    """Types of relationships between AST nodes."""
    CONTAINS = "CONTAINS"
    EXTENDS = "EXTENDS"
    IMPLEMENTS = "IMPLEMENTS"
    CALLS = "CALLS"
    DEPENDS_ON = "DEPENDS_ON"
    USES = "USES"
    IMPORTS = "IMPORTS"


class FileInfo(BaseModel):
    """Metadata about a parsed file or directory."""

    path: str = Field(..., description="Absolute path to file or directory")
    name: str = Field(..., description="Base name of file or directory")
    size: int = Field(default=0, description="File size in bytes (0 for directories)")
    language: str = Field(default="python", description="Programming language identifier")
    last_modified: Optional[datetime] = Field(default=None, description="Last modification timestamp")
    is_directory: bool = Field(default=False, description="True if parsing a directory")
    file_count: int = Field(default=1, description="Number of files parsed (1 for single file)")


class ASTNode(BaseModel):
    """A node in the Abstract Syntax Tree."""

    id: str = Field(..., description="Unique UUID identifier")
    type: str = Field(..., description="Node type (File, Class, Method, Variable)")
    name: str = Field(..., description="Name of the element")
    source_file: str = Field(..., description="Path to source file")
    start_line: int = Field(default=1, description="Starting line number (1-indexed)")
    end_line: int = Field(default=1, description="Ending line number (1-indexed)")
    start_column: int = Field(default=0, description="Starting column (0-indexed)")
    end_column: int = Field(default=0, description="Ending column (0-indexed)")
    signature: Optional[str] = Field(default=None, description="Full signature for Class/Method")
    decorators: Optional[List[str]] = Field(default=None, description="Decorator names")
    base_classes: Optional[List[str]] = Field(default=None, description="Base class names")
    data_type: Optional[str] = Field(default=None, description="Type annotation for Variable")
    module_path: Optional[str] = Field(default=None, description="Original dotted import path")
    language: str = Field(default="", description="Programming language identifier")


class CrossFileConfig(BaseModel):
    """Configuration for cross-file relationship detection."""
    imports: bool = True
    inheritance: bool = True
    calls: bool = True
    usage: bool = True
    include_external: bool = False


class RawImport(BaseModel):
    """Raw import data captured during first-pass parsing."""
    source_file: str
    source_file_node_id: str
    module: Optional[str] = None
    names: List[str]
    level: int


class UnresolvedReference(BaseModel):
    """Unresolved call or usage reference from first-pass parsing."""
    source_file: str
    source_node_id: str
    reference_name: str
    reference_type: str
    line: int


class Relationship(BaseModel):
    """A relationship between two AST nodes."""

    source_id: str = Field(..., description="UUID of source node")
    target_id: str = Field(..., description="UUID of target node")
    type: str = Field(..., description="Relationship type")


class ParseError(BaseModel):
    """An error encountered during parsing."""

    file_path: str = Field(..., description="Path to file where error occurred")
    line_number: Optional[int] = Field(default=None, description="Line number where error occurred")
    message: str = Field(..., description="Human-readable error message")


class Summary(BaseModel):
    """Summary statistics for parsed results."""

    total_files: int = Field(default=0, description="Number of files parsed")
    total_nodes: int = Field(default=0, description="Total nodes extracted")
    nodes_by_type: Dict[str, int] = Field(default_factory=dict, description="Count per node type")
    total_relationships: int = Field(default=0, description="Total relationships")
    relationships_by_type: Dict[str, int] = Field(default_factory=dict, description="Count per relationship type")
    total_errors: int = Field(default=0, description="Total errors encountered")
    parsing_duration_ms: float = Field(default=0.0, description="Time taken in milliseconds")


class ASTResult(BaseModel):
    """Complete result of parsing one or more source files."""

    file_info: Optional[FileInfo] = Field(default=None, description="Metadata about the parsed file(s)")
    nodes: List[ASTNode] = Field(default_factory=list, description="All nodes extracted from the AST")
    relationships: List[Relationship] = Field(default_factory=list, description="All relationships between nodes")
    errors: List[ParseError] = Field(default_factory=list, description="Errors encountered during parsing")
    summary: Summary = Field(default_factory=Summary, description="Summary statistics")
    raw_imports: List[RawImport] = Field(default_factory=list, description="Raw import data for cross-file resolution")
    unresolved_references: List[UnresolvedReference] = Field(default_factory=list, description="Unresolved cross-file references")
