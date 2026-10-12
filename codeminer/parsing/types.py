"""Type definitions for the multi-language parsing system."""

from enum import Enum
from pydantic import BaseModel


class NodeTypeDefinition(BaseModel):
    """Metadata for a node type — used by frontend for grouping and filtering."""

    name: str
    language: str
    category: str  # "structure", "callable", "data", "dependency"
    description: str


class RelationshipTypeDefinition(BaseModel):
    """Metadata for a relationship type."""

    name: str
    language: str
    category: str  # "structural", "inheritance", "dependency", "usage"
    description: str


class CoreNodeType(str, Enum):
    """Common node types shared across languages. Helper enum, not a constraint."""

    FILE = "File"
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


class CoreRelationshipType(str, Enum):
    """Common relationship types shared across languages."""

    CONTAINS = "CONTAINS"
    EXTENDS = "EXTENDS"
    IMPLEMENTS = "IMPLEMENTS"
    CALLS = "CALLS"
    DEPENDS_ON = "DEPENDS_ON"
    USES = "USES"
    IMPORTS = "IMPORTS"
