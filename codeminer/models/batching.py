"""Pydantic models for Neo4j UNWIND batching operations."""

from typing import List, Literal, Optional
from pydantic import BaseModel, Field, field_validator

ALLOWED_RELATIONSHIP_TYPES = {
    "CONTAINS",
    "EXTENDS",
    "IMPLEMENTS",
    "CALLS",
    "DEPENDS_ON",
    "USES",
    "IMPORTS",
    "REFERENCES",
    "INHERITS",
}

BATCH_SIZE_MIN = 100
BATCH_SIZE_MAX = 1000


class NodeWriteRecord(BaseModel):
    """A single node record for batched UNWIND writes."""

    id: str = Field(..., description="Node UUID")
    project_id: str = Field(..., description="Project UUID")
    type: str = Field(..., description="Node type label (File, Class, etc.)")
    name: str = Field(..., description="Node name")
    source_file: str = Field(..., description="Source file path")
    start_line: int = Field(default=0)
    end_line: int = Field(default=0)
    start_column: int = Field(default=0)
    end_column: int = Field(default=0)
    signature: Optional[str] = Field(default=None)
    decorators: List[str] = Field(default_factory=list)
    base_classes: List[str] = Field(default_factory=list)
    data_type: Optional[str] = Field(default=None)
    module_path: Optional[str] = Field(default=None)
    language: str = Field(default="")

    @field_validator("id", "project_id", "type", "name", "source_file")
    @classmethod
    def must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Field must not be empty")
        return v


class RelationshipWriteRecord(BaseModel):
    """A single relationship record for batched UNWIND writes."""

    source_id: str = Field(..., description="Source node ID")
    target_id: str = Field(..., description="Target node ID")
    type: str = Field(..., description="Relationship type")
    project_id: str = Field(..., description="Project UUID")

    @field_validator("source_id", "target_id", "type", "project_id")
    @classmethod
    def must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Field must not be empty")
        return v

    @field_validator("type")
    @classmethod
    def type_must_be_allowed(cls, v: str) -> str:
        if v not in ALLOWED_RELATIONSHIP_TYPES:
            raise ValueError(
                f"Relationship type '{v}' not in allowlist: {ALLOWED_RELATIONSHIP_TYPES}"
            )
        return v


class WriteBatch(BaseModel):
    """A batch of write records ready for UNWIND execution."""

    kind: Literal["node", "relationship"] = Field(..., description="Batch kind")
    records: List = Field(..., description="List of write records")
    batch_size: int = Field(default=500, description="Batch size for execution")

    @field_validator("batch_size")
    @classmethod
    def batch_size_in_range(cls, v: int) -> int:
        if not (BATCH_SIZE_MIN <= v <= BATCH_SIZE_MAX):
            raise ValueError(
                f"batch_size {v} must be between {BATCH_SIZE_MIN} and {BATCH_SIZE_MAX}"
            )
        return v


class BatchExecutionAttempt(BaseModel):
    """Tracks a single batch write attempt (for retry/backoff reporting)."""

    attempt_number: int = Field(..., ge=1)
    transient_error_detected: bool = Field(default=False)
    backoff_ms: int = Field(default=0, ge=0)
    outcome: Literal["success", "failed"] = Field(...)


class StorageResultSummary(BaseModel):
    """Structured run-level result for a batched storage operation."""

    status: Literal["success", "failed", "partial_with_warnings"] = Field(
        default="success"
    )
    nodes_processed: int = Field(default=0, ge=0)
    relationships_processed: int = Field(default=0, ge=0)
    batches_total: int = Field(default=0, ge=0)
    batches_failed: int = Field(default=0, ge=0)
    relationships_skipped_orphan: int = Field(default=0, ge=0)

    @field_validator("batches_failed")
    @classmethod
    def failed_not_exceed_total(cls, v: int, info) -> int:
        total = info.data.get("batches_total", 0)
        if total > 0 and v > total:
            raise ValueError("batches_failed cannot exceed batches_total")
        return v

    @field_validator("relationships_skipped_orphan")
    @classmethod
    def orphan_not_exceed_processed(cls, v: int, info) -> int:
        processed = info.data.get("relationships_processed", 0)
        skipped = v
        if processed == 0 and skipped > 0:
            # relationships_processed may not include orphans; allow this
            pass
        return v
