"""
Graph Storage - Neo4j operations for AST graph data.

Provides storage and query operations for AST nodes and relationships,
including UNWIND-batched storage, type-based queries, and graph summaries.

Batching strategy (see specs/011-neo4j-unwind-batching/contracts/graph-storage-batching.md):
- Nodes are grouped by label class and stored via UNWIND (one query per label group).
- Relationships are grouped by type and stored via UNWIND (one query per type group).
- Orphan relationships (referencing missing nodes) are skipped and counted as warnings.
- Non-orphan batch failures trigger atomic rollback.
- Transient failures are retried up to 3 times with exponential backoff.
"""

import logging
import time
from collections import defaultdict
from typing import Any, Callable, Dict, List, Optional, Set, TypeVar

from neo4j.exceptions import ServiceUnavailable, SessionExpired

try:
    from neo4j.exceptions import TransientError as Neo4jTransientError
except ImportError:
    Neo4jTransientError = None  # type: ignore[assignment,misc]

from .models import StorageResult, GraphSummary
from .neo4j_manager import Neo4jConnectionManager
from ..config import settings
from ..models.batching import StorageResultSummary
from ..parsing.models import ASTResult, ASTNode, Relationship

logger = logging.getLogger(__name__)

T = TypeVar("T")

_BATCH_SIZE_MIN = 100
_BATCH_SIZE_MAX = 1000
_MAX_RETRY_ATTEMPTS = 3


class GraphStorageError(Exception):
    """Exception raised for graph storage errors.

    Attributes:
        message: Human-readable error description.
        error_code: Machine-readable code for programmatic handling.
        batch_id: Optional identifier of the failing batch.
        attempt_details: Summary of retry attempts made before failure.
        failure_policy_applied: Whether the failure policy (rollback) was applied.
    """

    def __init__(
        self,
        message: str,
        error_code: str = "STORAGE_ERROR",
        batch_id: Optional[str] = None,
        attempt_details: Optional[str] = None,
        failure_policy_applied: bool = False,
    ) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.batch_id = batch_id
        self.attempt_details = attempt_details
        self.failure_policy_applied = failure_policy_applied


class GraphStorage:
    """Neo4j storage for AST graph data.

    Provides operations for storing and querying AST graph data
    including UNWIND-batched nodes/relationships, type-based queries,
    and graph summaries.

    Attributes:
        connection_manager: Neo4j connection manager

    Example:
        >>> config = DatabaseConfig()
        >>> manager = Neo4jConnectionManager(config)
        >>> storage = GraphStorage(manager)
        >>> result = storage.store_ast_result(project_id, ast_result)
    """

    # Cypher queries — legacy single-record CREATE (kept for reference)
    CYPHER_CREATE_FILE = """
        CREATE (n:ASTNode:File
    """
    CYPHER_CREATE_NODE = """
        CREATE (n:ASTNode
    """
    CYPHER_CREATE_CLASS = """
        CREATE (n:ASTNode:Class
    """
    CYPHER_CREATE_EXTERNAL_MODULE = """
        CREATE (n:ASTNode:ExternalModule
    """

    CYPHER_CREATE_BODY = """
        {
            id: $id,
            type: $type,
            name: $name,
            source_file: $source_file,
            start_line: $start_line,
            end_line: $end_line,
            start_column: $start_column,
            end_column: $end_column,
            signature: $signature,
            decorators: $decorators,
            base_classes: $base_classes,
            data_type: $data_type,
            module_path: $module_path,
            language: $language,
            project_id: $project_id
        })
    """

    # UNWIND batch write templates — one query per label / relationship type
    _CYPHER_UNWIND_NODES_TEMPLATE = """
        UNWIND $nodes AS props
        CREATE (n{label_clause})
        SET n = props
    """

    _LABEL_MAP: Dict[str, str] = {
        "File": ":ASTNode:File",
        "Class": ":ASTNode:Class",
        "ExternalModule": ":ASTNode:ExternalModule",
    }
    _DEFAULT_LABEL = ":ASTNode"

    CYPHER_CREATE_RELATIONSHIP = """
        MATCH (source:ASTNode {id: $source_id, project_id: $project_id})
        MATCH (target:ASTNode {id: $target_id, project_id: $project_id})
        CREATE (source)-[r:` + rel_type + ` {
            source_id: $source_id,
            target_id: $target_id,
            type: $type,
            project_id: $project_id
        }]->(target)
        RETURN r
    """

    CYPHER_QUERY_NODES_BY_TYPE = """
        MATCH (n:ASTNode {project_id: $project_id, type: $node_type})
        WHERE ($source_file IS NULL OR n.source_file = $source_file)
          AND ($language IS NULL OR n.language = $language)
        RETURN n {
            .id, .type, .name, .source_file, .language,
            .start_line, .end_line, .start_column, .end_column,
            .signature, .decorators, .base_classes, .data_type
        } as node
        ORDER BY n.start_line
        LIMIT $limit
    """

    CYPHER_QUERY_NODES_BY_PROJECT = """
        MATCH (n:ASTNode {project_id: $project_id})
        WHERE ($source_file IS NULL OR n.source_file = $source_file)
          AND ($language IS NULL OR n.language = $language)
        RETURN n {
            .id, .type, .name, .source_file, .language,
            .start_line, .end_line, .start_column, .end_column,
            .signature, .decorators, .base_classes, .data_type
        } as node
        ORDER BY n.type, n.start_line
        LIMIT $limit
    """
    # TODO Query is not used and may be removed in future iterations, but leaving in for now as it may be useful for debugging and exploration
    CYPHER_QUERY_RELATIONSHIPS = """
        MATCH (source:ASTNode {project_id: $project_id})
        -[r:` + rel_type + ` {project_id: $project_id}]->
        (target:ASTNode {project_id: $project_id})
        RETURN {
            source_id: r.source_id,
            target_id: r.target_id,
            type: r.type,
            project_id: r.project_id,
            source: source {
                .id, .type, .name, .source_file
            },
            target: target {
                .id, .type, .name, .source_file
            }
        } as relationship
        LIMIT $limit
    """
    # TODO Query is not used and may be removed in future iterations, but leaving in for now as it may be useful for debugging and exploration
    CYPHER_QUERY_ALL_RELATIONSHIPS = """
        MATCH (source:ASTNode {project_id: $project_id})
        -[r {project_id: $project_id}]->
        (target:ASTNode {project_id: $project_id})
        RETURN {
            source_id: r.source_id,
            target_id: r.target_id,
            type: r.type,
            project_id: r.project_id,
            source: source {
                .id, .type, .name, .source_file
            },
            target: target {
                .id, .type, .name, .source_file
            }
        } as relationship
        ORDER BY type(r), r.source_id
        LIMIT $limit
    """

    CYPHER_GET_NODE_BY_ID = """
        MATCH (n:ASTNode {project_id: $project_id, id: $node_id})
        RETURN n {
            .id, .type, .name, .source_file, .language,
            .start_line, .end_line, .start_column, .end_column,
            .signature, .decorators, .base_classes, .data_type
        } as node
        LIMIT 1
    """
    CYPHER_QUERY_PROJECT_RELATIONSHIPS = """
        MATCH (source:ASTNode {project_id: $project_id})
        -[r {project_id: $project_id}]->
        (target:ASTNode {project_id: $project_id})
        RETURN {
            source_id: r.source_id,
            target_id: r.target_id,
            type: r.type,
            project_id: r.project_id,
            source: source {
                .id, .type, .name, .source_file, .language
            },
            target: target {
                .id, .type, .name, .source_file, .language
            }
        } as relationship
        ORDER BY r.type, r.source_id
        LIMIT $limit
    """

    CYPHER_SEARCH_NODES = """
        MATCH (n:ASTNode {project_id: $project_id})
        WHERE toLower(n.name) CONTAINS toLower($search_term)
        AND ($node_type IS NULL OR n.type = $node_type)
        RETURN n {
            .id, .type, .name, .source_file, .language,
            .start_line, .end_line, .start_column, .end_column,
            .signature, .decorators, .base_classes, .data_type
        } as node
        ORDER BY n.type, n.start_line
        LIMIT $limit
    """

    CYPHER_GET_RELATIONSHIPS_FOR_NODE = """
        MATCH (node:ASTNode {project_id: $project_id, id: $node_id})
        OPTIONAL MATCH (source:ASTNode {project_id: $project_id})
        -[r {project_id: $project_id}]->
        (target:ASTNode {project_id: $project_id})
        WHERE (
            $direction = 'outgoing' AND source.id = node.id
        ) OR (
            $direction = 'incoming' AND target.id = node.id
        ) OR (
            $direction = 'both' AND (source.id = node.id OR target.id = node.id)
        )
        RETURN {
            source_id: r.source_id,
            target_id: r.target_id,
            type: r.type,
            project_id: r.project_id,
            source: source {
                .id, .type, .name, .source_file
            },
            target: target {
                .id, .type, .name, .source_file
            }
        } as relationship
    """

    CYPHER_GET_NODE_COUNT = """
        MATCH (n:ASTNode {project_id: $project_id})
        RETURN count(n) as count
    """

    CYPHER_GET_RELATIONSHIP_COUNT = """
        MATCH (:ASTNode {project_id: $project_id})-[r {project_id: $project_id}]->(:ASTNode {project_id: $project_id})
        RETURN count(r) as count
    """

    CYPHER_DELETE_BY_PROJECT = """
        MATCH (n:ASTNode {project_id: $project_id})
        DETACH DELETE n
        RETURN count(n) as deleted_count
    """

    CYPHER_DELETE_RELATIONSHIPS = """
        MATCH (n:ASTNode {project_id: $project_id})-[r]->()
        DELETE r
        RETURN count(r) as deleted_count
    """
    CYPHER_DELETE_ALL_RELATIONSHIPS = """
        MATCH ()-[r]->()
        DELETE r
        RETURN count(r) as deleted_count
    """
    CYPHER_DELETE_ALL_NODES = """
        MATCH (n:ASTNode)
        DETACH DELETE n
        RETURN count(n) as deleted_count
    """

    def __init__(self, connection_manager: Neo4jConnectionManager) -> None:
        """Initialize graph storage.

        Args:
            connection_manager: Neo4j connection manager
        """
        self.connection_manager = connection_manager

    # -------------------------------------------------------------------------
    # Helper utilities (T011-T014)
    # -------------------------------------------------------------------------

    @staticmethod
    def _validate_batch_size(batch_size: int) -> int:
        """Validate batch size is within the allowed guardrail range [100, 1000].

        Args:
            batch_size: Requested batch size.

        Returns:
            Validated batch size.

        Raises:
            ValueError: If batch_size is outside [100, 1000].
        """
        if not (_BATCH_SIZE_MIN <= batch_size <= _BATCH_SIZE_MAX):
            raise ValueError(
                f"batch_size={batch_size} is outside the allowed range "
                f"[{_BATCH_SIZE_MIN}, {_BATCH_SIZE_MAX}]. "
                f"Please set a value between {_BATCH_SIZE_MIN} and {_BATCH_SIZE_MAX}."
            )
        return batch_size

    @staticmethod
    def _calculate_exponential_backoff(attempt_number: int) -> int:
        """Calculate exponential backoff in milliseconds for a retry attempt.

        Args:
            attempt_number: 1-based attempt index (first retry = 1).

        Returns:
            Backoff duration in milliseconds: 100 * 2^(attempt_number - 1).
        """
        return 100 * (2 ** (attempt_number - 1))

    @staticmethod
    def _is_transient_error(exception: Exception) -> bool:
        """Return True if the exception represents a retryable Neo4j condition.

        Detects transient errors: connection timeouts, session expiry, service
        unavailability, and Neo4j's own TransientError class when available.

        Args:
            exception: Exception to inspect.

        Returns:
            True if the exception is considered retryable.
        """
        if Neo4jTransientError is not None and isinstance(
            exception, Neo4jTransientError
        ):
            return True
        if isinstance(exception, (ServiceUnavailable, SessionExpired)):
            return True
        msg = str(exception).lower()
        return any(
            kw in msg
            for kw in ("timeout", "timed out", "connection reset", "write conflict")
        )

    @staticmethod
    def _group_records_by_category(
        records: List[T], group_key_fn: Callable[[T], str]
    ) -> Dict[str, List[T]]:
        """Partition records into groups by the key returned by *group_key_fn*.

        Args:
            records: Iterable of records to group.
            group_key_fn: Function that extracts the grouping key from a record.

        Returns:
            Mapping of key → list of records belonging to that group.
        """
        groups: Dict[str, List[T]] = defaultdict(list)
        for record in records:
            groups[group_key_fn(record)].append(record)
        return dict(groups)

    # -------------------------------------------------------------------------
    # Parameter conversion
    # -------------------------------------------------------------------------

    def _node_to_params(self, node: ASTNode, project_id: str) -> Dict[str, Any]:
        """Convert ASTNode to Cypher parameters.

        Args:
            node: AST node to convert
            project_id: Project UUID

        Returns:
            Dictionary of Cypher parameters
        """
        return {
            "id": node.id,
            "type": node.type,
            "name": node.name,
            "source_file": node.source_file,
            "start_line": node.start_line,
            "end_line": node.end_line,
            "start_column": node.start_column,
            "end_column": node.end_column,
            "signature": node.signature,
            "decorators": node.decorators or [],
            "base_classes": node.base_classes or [],
            "data_type": node.data_type,
            "module_path": node.module_path,
            "language": getattr(node, "language", ""),
            "project_id": project_id,
        }

    # -------------------------------------------------------------------------
    # UNWIND batch write methods (T018-T020)
    # -------------------------------------------------------------------------

    def _store_node_batch(
        self,
        tx: Any,
        project_id: str,
        nodes: List[ASTNode],
        batch_size: Optional[int] = None,
    ) -> int:
        """Store nodes using UNWIND-batched Cypher writes grouped by label class.

        Nodes are partitioned by type (File, Class, ExternalModule, generic ASTNode)
        and written in batches of *batch_size* records per UNWIND statement,
        reducing network round-trips from O(n) to O(k) where k is the number of
        distinct label groups.

        Args:
            tx: Active Neo4j transaction.
            project_id: Project UUID.
            nodes: List of nodes to store.
            batch_size: Records per UNWIND call; defaults to config value.

        Returns:
            Number of nodes written.

        Raises:
            GraphStorageError: On non-transient write failure.
            ValueError: If batch_size is outside the allowed guardrail range.
        """
        if not nodes:
            return 0

        effective_size = self._validate_batch_size(
            batch_size if batch_size is not None else settings.graph_write_batch_size
        )

        # Group by label class
        label_groups = self._group_records_by_category(
            nodes, lambda n: n.type if n.type in self._LABEL_MAP else "_default"
        )

        count = 0
        for label_key, group in label_groups.items():
            label_clause = self._LABEL_MAP.get(label_key, self._DEFAULT_LABEL)
            cypher = self._CYPHER_UNWIND_NODES_TEMPLATE.replace(
                "{label_clause}", label_clause
            )
            # Send in sub-batches to respect batch_size
            for i in range(0, len(group), effective_size):
                sub_batch = group[i : i + effective_size]
                params_list = [self._node_to_params(n, project_id) for n in sub_batch]
                logger.debug(
                    "UNWIND node batch: label=%s count=%d project_id=%s",
                    label_clause,
                    len(params_list),
                    project_id,
                )
                tx.run(cypher, {"nodes": params_list})
                count += len(params_list)

        return count

    def _store_relationships(
        self,
        tx: Any,
        project_id: str,
        relationships: List[Relationship],
        stored_node_ids: Optional[Set[str]] = None,
        batch_size: Optional[int] = None,
    ) -> tuple[int, int]:
        """Store relationships using UNWIND-batched Cypher writes grouped by type.

        Orphan relationships (where the source or target node ID is not found in
        *stored_node_ids*) are silently skipped and their count is returned so the
        caller can surface a warning in the run-level result summary.

        Args:
            tx: Active Neo4j transaction.
            project_id: Project UUID.
            relationships: List of relationships to store.
            stored_node_ids: Optional set of node IDs already persisted this run;
                             used to detect orphan relationships.  When None, all
                             relationships are assumed to have valid endpoints.
            batch_size: Records per UNWIND call; defaults to config value.

        Returns:
            Tuple of (relationships_stored, orphans_skipped).

        Raises:
            GraphStorageError: On non-transient write failure.
            ValueError: If batch_size is outside the allowed guardrail range.
        """
        if not relationships:
            return 0, 0

        effective_size = self._validate_batch_size(
            batch_size if batch_size is not None else settings.graph_write_batch_size
        )

        valid_rels: List[Relationship] = []
        orphan_count = 0

        for rel in relationships:
            if stored_node_ids is not None and (
                rel.source_id not in stored_node_ids
                or rel.target_id not in stored_node_ids
            ):
                orphan_count += 1
                logger.warning(
                    "Orphan relationship skipped: type=%s source=%s target=%s project_id=%s",
                    rel.type,
                    rel.source_id,
                    rel.target_id,
                    project_id,
                )
            else:
                valid_rels.append(rel)

        if orphan_count:
            logger.warning(
                "Skipped %d orphan relationship(s) for project_id=%s",
                orphan_count,
                project_id,
            )

        # Group valid relationships by type and write with UNWIND
        type_groups = self._group_records_by_category(valid_rels, lambda r: r.type)
        stored = 0

        for rel_type, group in type_groups.items():
            cypher = (
                f"UNWIND $rels AS r\n"
                f"MATCH (source:ASTNode {{id: r.source_id, project_id: r.project_id}})\n"
                f"MATCH (target:ASTNode {{id: r.target_id, project_id: r.project_id}})\n"
                f"CREATE (source)-[rel:{rel_type} {{source_id: r.source_id, "
                f"target_id: r.target_id, type: r.type, "
                f"project_id: r.project_id}}]->(target)\n"
            )
            for i in range(0, len(group), effective_size):
                sub_batch = group[i : i + effective_size]
                params_list = [
                    {
                        "source_id": r.source_id,
                        "target_id": r.target_id,
                        "type": r.type,
                        "project_id": project_id,
                    }
                    for r in sub_batch
                ]
                logger.debug(
                    "UNWIND relationship batch: type=%s count=%d project_id=%s",
                    rel_type,
                    len(params_list),
                    project_id,
                )
                tx.run(cypher, {"rels": params_list})
                stored += len(params_list)

        return stored, orphan_count

    # -------------------------------------------------------------------------
    # Retry logic helpers (T036)
    # -------------------------------------------------------------------------

    def _execute_with_retry(
        self,
        operation: Callable[[], T],
        batch_id: str = "batch",
    ) -> T:
        """Execute *operation* with bounded exponential-backoff retry on transient errors.

        Retries up to _MAX_RETRY_ATTEMPTS times for transient Neo4j failures.
        Non-transient exceptions are re-raised immediately without retry.

        Args:
            operation: Zero-argument callable to attempt.
            batch_id: Human-readable identifier for logging.

        Returns:
            Return value of *operation* on success.

        Raises:
            GraphStorageError: After retry exhaustion or on non-transient failure.
        """
        last_exc: Optional[Exception] = None
        for attempt in range(1, _MAX_RETRY_ATTEMPTS + 2):  # 1 initial + 3 retries
            try:
                return operation()
            except Exception as exc:
                if not self._is_transient_error(exc):
                    raise GraphStorageError(
                        f"Non-transient error during {batch_id}: {exc}",
                        error_code="BATCH_WRITE_ERROR",
                        batch_id=batch_id,
                        failure_policy_applied=True,
                    ) from exc

                last_exc = exc
                if attempt <= _MAX_RETRY_ATTEMPTS:
                    backoff = self._calculate_exponential_backoff(attempt)
                    logger.warning(
                        "Transient error on attempt %d/%d for %s; backoff=%dms: %s",
                        attempt,
                        _MAX_RETRY_ATTEMPTS + 1,
                        batch_id,
                        backoff,
                        exc,
                    )
                    time.sleep(backoff / 1000.0)
                else:
                    logger.error(
                        "Retry exhausted after %d attempts for %s: %s",
                        _MAX_RETRY_ATTEMPTS + 1,
                        batch_id,
                        exc,
                    )

        raise GraphStorageError(
            f"Retry exhausted ({_MAX_RETRY_ATTEMPTS} retries) for {batch_id}: {last_exc}",
            error_code="RETRY_EXHAUSTED",
            batch_id=batch_id,
            attempt_details=f"{_MAX_RETRY_ATTEMPTS} retries attempted",
            failure_policy_applied=True,
        ) from last_exc

    # -------------------------------------------------------------------------
    # Main entry point (T021, T037-T038)
    # -------------------------------------------------------------------------

    def store_ast_result(
        self,
        project_id: str,
        ast_result: ASTResult,
        batch_size: Optional[int] = None,
    ) -> StorageResult:
        """Store AST graph data in Neo4j using UNWIND batching.

        Nodes are partitioned by label class and relationships are partitioned by
        type; each group is written in a single UNWIND statement per sub-batch,
        reducing round-trips dramatically over the legacy per-record CREATE path.

        Orphan relationships (referencing missing nodes) are skipped with a warning
        and the count is surfaced in *result.summary*.  Any non-orphan batch failure
        triggers a full atomic rollback via the transaction context manager.

        Args:
            project_id: Project UUID.
            ast_result: AST result from the parser.
            batch_size: Records per UNWIND call.  Defaults to
                ``settings.graph_write_batch_size`` (500).

        Returns:
            StorageResult with node/relationship counts, duration, and a nested
            ``StorageResultSummary`` accessible as ``result.summary``.

        Raises:
            GraphStorageError: If storage fails after retries.
        """
        effective_size = self._validate_batch_size(
            batch_size if batch_size is not None else settings.graph_write_batch_size
        )

        start_time = time.time()
        nodes_stored = 0
        relationships_stored = 0
        orphans_skipped = 0
        files_stored = 0
        batches_total = 0
        batches_failed = 0
        final_status = "success"
        stored_node_ids: Set[str] = set()

        try:
            with self.connection_manager.transaction() as tx:
                # --- Node writes ---
                nodes = ast_result.nodes
                if nodes:
                    # Determine batch boundaries by label group
                    label_groups = self._group_records_by_category(
                        nodes,
                        lambda n: n.type if n.type in self._LABEL_MAP else "_default",
                    )
                    for label_key, group in label_groups.items():
                        for i in range(0, len(group), effective_size):
                            batches_total += 1
                            sub_batch = group[i : i + effective_size]
                            label_clause = self._LABEL_MAP.get(
                                label_key, self._DEFAULT_LABEL
                            )
                            cypher = self._CYPHER_UNWIND_NODES_TEMPLATE.replace(
                                "{label_clause}", label_clause
                            )
                            params_list = [
                                self._node_to_params(n, project_id) for n in sub_batch
                            ]
                            logger.debug(
                                "Writing node batch %d: label=%s count=%d project_id=%s",
                                batches_total,
                                label_clause,
                                len(params_list),
                                project_id,
                            )
                            tx.run(cypher, {"nodes": params_list})
                            nodes_stored += len(params_list)
                            stored_node_ids.update(n.id for n in sub_batch)

                # --- Relationship writes ---
                if ast_result.relationships:
                    valid_rels: List[Relationship] = []
                    for rel in ast_result.relationships:
                        if (
                            rel.source_id not in stored_node_ids
                            or rel.target_id not in stored_node_ids
                        ):
                            orphans_skipped += 1
                            logger.warning(
                                "Orphan relationship skipped: type=%s source=%s "
                                "target=%s project_id=%s",
                                rel.type,
                                rel.source_id,
                                rel.target_id,
                                project_id,
                            )
                        else:
                            valid_rels.append(rel)

                    if orphans_skipped:
                        logger.warning(
                            "Skipped %d orphan relationship(s) for project_id=%s",
                            orphans_skipped,
                            project_id,
                        )

                    type_groups = self._group_records_by_category(
                        valid_rels, lambda r: r.type
                    )
                    for rel_type, group in type_groups.items():
                        for i in range(0, len(group), effective_size):
                            batches_total += 1
                            sub_batch = group[i : i + effective_size]
                            cypher = (
                                f"UNWIND $rels AS r\n"
                                f"MATCH (source:ASTNode {{id: r.source_id, "
                                f"project_id: r.project_id}})\n"
                                f"MATCH (target:ASTNode {{id: r.target_id, "
                                f"project_id: r.project_id}})\n"
                                f"CREATE (source)-[rel:{rel_type} {{"
                                f"source_id: r.source_id, "
                                f"target_id: r.target_id, type: r.type, "
                                f"project_id: r.project_id}}]->(target)\n"
                            )
                            params_list = [
                                {
                                    "source_id": r.source_id,
                                    "target_id": r.target_id,
                                    "type": r.type,
                                    "project_id": project_id,
                                }
                                for r in sub_batch
                            ]
                            logger.debug(
                                "Writing relationship batch %d: type=%s count=%d "
                                "project_id=%s",
                                batches_total,
                                rel_type,
                                len(params_list),
                                project_id,
                            )
                            tx.run(cypher, {"rels": params_list})
                            relationships_stored += len(params_list)

                files_stored = 1 if ast_result.file_info else 0

        except GraphStorageError:
            batches_failed += 1
            final_status = "failed"
            raise
        except Exception as exc:
            batches_failed += 1
            final_status = "failed"
            logger.error(
                "Failed to store AST graph for project %s: %s", project_id, exc
            )
            raise GraphStorageError(
                f"Storage failed: {exc}",
                error_code="STORAGE_ERROR",
                failure_policy_applied=True,
            ) from exc

        duration_ms = (time.time() - start_time) * 1000

        if orphans_skipped > 0 and final_status == "success":
            final_status = "partial_with_warnings"

        summary = StorageResultSummary(
            status=final_status,
            nodes_processed=nodes_stored,
            relationships_processed=relationships_stored,
            batches_total=batches_total,
            batches_failed=batches_failed,
            relationships_skipped_orphan=orphans_skipped,
        )

        result = StorageResult(
            files_stored=files_stored,
            nodes_stored=nodes_stored,
            relationships_stored=relationships_stored,
            duration_ms=duration_ms,
        )
        result.summary = summary

        logger.info(
            "Stored AST graph [%s]: %d nodes, %d relationships, "
            "%d orphans skipped, %d batches in %.1fms (project_id=%s)",
            final_status,
            nodes_stored,
            relationships_stored,
            orphans_skipped,
            batches_total,
            duration_ms,
            project_id,
        )

        return result

    def query_nodes_by_type(
        self,
        project_id: str,
        node_type: str,
        source_file: Optional[str] = None,
        language: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Query nodes by type.

        Args:
            project_id: Project UUID
            node_type: Node type to filter (File, Class, Method, Variable)
            source_file: Optional source file path filter
            language: Optional programming language filter
            limit: Maximum number of nodes to return

        Returns:
            List of node dictionaries

        Raises:
            GraphStorageError: If query fails
        """
        try:
            with self.connection_manager.get_session() as session:
                result = session.run(
                    self.CYPHER_QUERY_NODES_BY_TYPE,
                    {
                        "project_id": project_id,
                        "node_type": node_type,
                        "source_file": source_file,
                        "language": language,
                        "limit": limit,
                    },
                )

                nodes = [record["node"] for record in result]
                logger.debug(f"Queried {len(nodes)} nodes of type {node_type}")
                return nodes

        except Exception as e:
            logger.error(f"Failed to query nodes: {e}")
            raise GraphStorageError(f"Query failed: {e}")

    def query_nodes_by_project(
        self,
        project_id: str,
        source_file: Optional[str] = None,
        language: Optional[str] = None,
        limit: int = 1000,
    ) -> List[Dict[str, Any]]:
        """Query all nodes for a project.

        Args:
            project_id: Project UUID
            source_file: Optional source file path filter
            language: Optional programming language filter
            limit: Maximum number of nodes to return

        Returns:
            List of node dictionaries

        Raises:
            GraphStorageError: If query fails
        """
        try:
            with self.connection_manager.get_session() as session:
                result = session.run(
                    self.CYPHER_QUERY_NODES_BY_PROJECT,
                    {
                        "project_id": project_id,
                        "source_file": source_file,
                        "language": language,
                        "limit": limit,
                    },
                )

                nodes = [record["node"] for record in result]
                logger.debug(f"Queried {len(nodes)} nodes for project {project_id}")
                return nodes

        except Exception as e:
            logger.error(f"Failed to query nodes: {e}")
            raise GraphStorageError(f"Query failed: {e}")
    # @TODO: method is unused and may be removed in future iterations, but leaving in for now as it may be useful for debugging and exploration
    def query_relationships(
        self, project_id: str, relationship_type: Optional[str] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Query relationships.

        Args:
            project_id: Project UUID
            relationship_type: Optional relationship type filter
            limit: Maximum number of relationships to return

        Returns:
            List of relationship dictionaries with source/target node data

        Raises:
            GraphStorageError: If query fails
        """
        try:
            with self.connection_manager.get_session() as session:
                # Choose query based on relationship type
                if relationship_type:
                    query = self.CYPHER_QUERY_RELATIONSHIPS.replace(
                        "rel_type", relationship_type
                    )
                else:
                    query = self.CYPHER_QUERY_ALL_RELATIONSHIPS

                result = session.run(query, {"project_id": project_id, "limit": limit})

                relationships = [record["relationship"] for record in result]
                logger.debug(
                    f"Queried {len(relationships)} relationships "
                    f'{"of type " + relationship_type if relationship_type else ""}'
                )
                return relationships

        except Exception as e:
            logger.error(f"Failed to query relationships: {e}")
            raise GraphStorageError(f"Query failed: {e}")

    def get_node_by_id(self, project_id: str, node_id: str) -> Optional[Dict[str, Any]]:
        """Get a single node by project and node id.

        Args:
            project_id: Project UUID
            node_id: Node ID

        Returns:
            Node dictionary if found, else None

        Raises:
            GraphStorageError: If query fails
        """
        try:
            with self.connection_manager.get_session() as session:
                result = session.run(
                    self.CYPHER_GET_NODE_BY_ID,
                    {"project_id": project_id, "node_id": node_id},
                )
                record = result.single()
                return record["node"] if record else None

        except Exception as e:
            logger.error(f"Failed to get node by id: {e}")
            raise GraphStorageError(f"Node lookup failed: {e}")

    def search_nodes(
        self,
        project_id: str,
        search_term: str,
        node_type: Optional[str] = None,
        limit: int = 1000,
    ) -> List[Dict[str, Any]]:
        """Search nodes by partial case-insensitive name match.

        Args:
            project_id: Project UUID
            search_term: Search term matched against node name
            node_type: Optional node type filter
            limit: Maximum number of nodes to return

        Returns:
            List of matching node dictionaries

        Raises:
            GraphStorageError: If query fails
        """
        try:
            with self.connection_manager.get_session() as session:
                result = session.run(
                    self.CYPHER_SEARCH_NODES,
                    {
                        "project_id": project_id,
                        "search_term": search_term,
                        "node_type": node_type,
                        "limit": limit,
                    },
                )
                nodes = [record["node"] for record in result]
                logger.debug(f"Found {len(nodes)} nodes matching '{search_term}'")
                return nodes

        except Exception as e:
            logger.error(f"Failed to search nodes: {e}")
            raise GraphStorageError(f"Search failed: {e}")

    def get_relationships_for_node(
        self, project_id: str, node_id: str, direction: str = "both"
    ) -> List[Dict[str, Any]]:
        """Get relationships connected to a node.

        Args:
            project_id: Project UUID
            node_id: Node ID
            direction: incoming, outgoing, or both

        Returns:
            List of relationship dictionaries

        Raises:
            GraphStorageError: If query fails
        """
        try:
            with self.connection_manager.get_session() as session:
                result = session.run(
                    self.CYPHER_GET_RELATIONSHIPS_FOR_NODE,
                    {
                        "project_id": project_id,
                        "node_id": node_id,
                        "direction": direction,
                    },
                )
                relationships = [
                    record["relationship"]
                    for record in result
                    if record.get("relationship") is not None
                ]
                logger.debug(
                    f"Found {len(relationships)} {direction} relationships for node {node_id}"
                )
                return relationships

        except Exception as e:
            logger.error(f"Failed to get node relationships: {e}")
            raise GraphStorageError(f"Relationship lookup failed: {e}")

    def query_project_relationships(
        self,
        project_id: str,
        types: Optional[List[str]] = None,
        limit: int = 1000,
    ) -> List[Dict[str, Any]]:
        """Get all relationships for a project with optional type-set filtering.

        Args:
            project_id: Project UUID string
            types: Optional list of relationship type strings.
                   None or empty list returns all relationship types.
            limit: Maximum number of relationships to return.

        Returns:
            List of relationship dictionaries

        Raises:
            GraphStorageError: If query fails
        """
        try:
            with self.connection_manager.get_session() as session:
                result = session.run(
                    self.CYPHER_QUERY_PROJECT_RELATIONSHIPS,
                    {
                        "project_id": project_id,
                        "types": types if types is not None else [],
                        "limit": limit,
                    },
                )
                relationships = [
                    record["relationship"]
                    for record in result
                    if record.get("relationship") is not None
                ]
                logger.debug(
                    f"Found {len(relationships)} relationships for project {project_id}"
                )
                return relationships

        except Exception as e:
            logger.error(f"Failed to query project relationships: {e}")
            raise GraphStorageError(f"Project relationship query failed: {e}")

    def get_node_count(self, project_id: str) -> int:
        """Get total node count for a project."""
        try:
            with self.connection_manager.get_session() as session:
                result = session.run(
                    self.CYPHER_GET_NODE_COUNT, {"project_id": project_id}
                )
                record = result.single()
                return int(record["count"]) if record else 0

        except Exception as e:
            logger.error(f"Failed to count nodes: {e}")
            raise GraphStorageError(f"Node count failed: {e}")

    def get_relationship_count(self, project_id: str) -> int:
        """Get total relationship count for a project."""
        try:
            with self.connection_manager.get_session() as session:
                result = session.run(
                    self.CYPHER_GET_RELATIONSHIP_COUNT, {"project_id": project_id}
                )
                record = result.single()
                return int(record["count"]) if record else 0

        except Exception as e:
            logger.error(f"Failed to count relationships: {e}")
            raise GraphStorageError(f"Relationship count failed: {e}")

    def get_summary(self, project_id: str) -> GraphSummary:
        """Get graph summary for a project.

        Args:
            project_id: Project UUID

        Returns:
            Graph summary with node and relationship counts

        Raises:
            GraphStorageError: If query fails
        """
        try:
            with self.connection_manager.get_session() as session:
                # Build summary query dynamically
                # Note: This is a simplified version - production would use
                # a more efficient single-query approach

                # Get total nodes and by type
                node_result = session.run(
                    """
                    MATCH (n:ASTNode {project_id: $project_id})
                    RETURN n.type as type, count(n) as count
                    ORDER BY count DESC
                """,
                    {"project_id": project_id},
                )

                nodes_by_type = {
                    record["type"]: record["count"] for record in node_result
                }
                total_nodes = sum(nodes_by_type.values())

                # Get total relationships and by type
                rel_result = session.run(
                    """
                    MATCH (source:ASTNode {project_id: $project_id})
                    -[r]->(target:ASTNode {project_id: $project_id})
                    RETURN type(r) as type, count(r) as count
                    ORDER BY count DESC
                """,
                    {"project_id": project_id},
                )

                relationships_by_type = {
                    record["type"]: record["count"] for record in rel_result
                }
                total_relationships = sum(relationships_by_type.values())

                return GraphSummary(
                    total_nodes=total_nodes,
                    nodes_by_type=nodes_by_type,
                    total_relationships=total_relationships,
                    relationships_by_type=relationships_by_type,
                )

        except Exception as e:
            logger.error(f"Failed to get graph summary: {e}")
            raise GraphStorageError(f"Summary query failed: {e}")

    def delete_all(self) -> int:
        """Delete all graph data from the database.

        Deletes all nodes and relationships.

        Returns:
            Total number of deleted nodes and relationships
        Raises:
            GraphStorageError: If deletion fails
        """
        try:
            with self.connection_manager.get_session() as session:
                # Delete all relationships first
                rel_result = session.run(self.CYPHER_DELETE_ALL_RELATIONSHIPS)
                record = rel_result.single()
                rel_count = record["deleted_count"] if record else 0

                # Delete all nodes
                node_result = session.run(self.CYPHER_DELETE_ALL_NODES)
                record = node_result.single()
                node_count = record["deleted_count"] if record else 0

                total_deleted = node_count + rel_count
                logger.info(
                    f"Deleted all graph data: {node_count} nodes, {rel_count} relationships"
                )
                return total_deleted

        except Exception as e:
            logger.error(f"Failed to delete all graph data: {e}")
            raise GraphStorageError(f"Full deletion failed: {e}")

    def delete_by_project(self, project_id: str) -> int:
        """Delete all graph data for a project.

        Deletes both nodes and relationships.

        Args:
            project_id: Project UUID

        Returns:
            Total number of deleted nodes and relationships

        Raises:
            GraphStorageError: If deletion fails
        """
        try:
            with self.connection_manager.transaction() as tx:
                # Delete relationships first
                rel_result = tx.run(
                    self.CYPHER_DELETE_RELATIONSHIPS, {"project_id": project_id}
                )
                record = rel_result.single()
                rel_count = record["deleted_count"] if record else 0

                # Delete nodes (DETACH DELETE handles remaining relationships)
                node_result = tx.run(
                    self.CYPHER_DELETE_BY_PROJECT, {"project_id": project_id}
                )
                node_record = node_result.single()
                node_count = node_record["deleted_count"] if node_record else 0

                total_deleted = node_count + rel_count
                logger.info(
                    f"Deleted graph data for project {project_id}: "
                    f"{node_count} nodes, {rel_count} relationships"
                )

                return total_deleted

        except Exception as e:
            logger.error(f"Failed to delete graph data: {e}")
            raise GraphStorageError(f"Deletion failed: {e}")

    def delete_nodes_by_project(self, project_id: str) -> int:
        """Delete all AST nodes for a project.

        Uses DETACH DELETE to remove nodes and any attached relationships.

        Args:
            project_id: Project UUID

        Returns:
            Number of deleted nodes

        Raises:
            GraphStorageError: If deletion fails
        """
        try:
            with self.connection_manager.transaction() as tx:
                result = tx.run(
                    self.CYPHER_DELETE_BY_PROJECT, {"project_id": project_id}
                )
                record = result.single()
                count = record["deleted_count"] if record else 0

                logger.info(f"Deleted {count} nodes for project {project_id}")
                return count

        except Exception as e:
            logger.error(f"Failed to delete nodes: {e}")
            raise GraphStorageError(f"Node deletion failed: {e}")

    def delete_relationships_by_project(self, project_id: str) -> int:
        """Delete all relationships for a project.

        Args:
            project_id: Project UUID

        Returns:
            Number of deleted relationships

        Raises:
            GraphStorageError: If deletion fails
        """
        try:
            with self.connection_manager.transaction() as tx:
                result = tx.run(
                    self.CYPHER_DELETE_RELATIONSHIPS, {"project_id": project_id}
                )
                record = result.single()
                count = record["deleted_count"] if record else 0

                logger.info(f"Deleted {count} relationships for project {project_id}")
                return count

        except Exception as e:
            logger.error(f"Failed to delete relationships: {e}")
            raise GraphStorageError(f"Relationship deletion failed: {e}")

    def delete_nodes_by_type(
        self, project_id: str, node_types: list[str] | None = None
    ) -> int:
        """Delete nodes of specific type(s) for a project.

        Args:
            project_id: Project UUID
            node_types: List of node types to delete (e.g., ['Method', 'Variable']).
                       If None, deletes all node types.

        Returns:
            Number of deleted nodes

        Raises:
            GraphStorageError: If deletion fails
        """
        try:
            with self.connection_manager.transaction() as tx:
                if node_types:
                    # Build query for specific types
                    type_placeholders = ", ".join(
                        ["$type" + str(i) for i in range(len(node_types))]
                    )
                    query = f"""
                        MATCH (n:ASTNode {{project_id: $project_id}})
                        WHERE n.type IN [{type_placeholders}]
                        DETACH DELETE n
                        RETURN count(n) as deleted_count
                    """
                    params: dict = {"project_id": project_id}
                    params.update({f"type{i}": t for i, t in enumerate(node_types)})
                else:
                    # Delete all nodes
                    query = self.CYPHER_DELETE_BY_PROJECT
                    params = {"project_id": project_id}

                result = tx.run(query, params)
                record = result.single()
                count = record["deleted_count"] if record else 0

                logger.info(
                    f'Deleted {count} nodes of type(s) {node_types or "all"} '
                    f"for project {project_id}"
                )
                return count

        except Exception as e:
            logger.error(f"Failed to delete nodes by type: {e}")
            raise GraphStorageError(f"Type-based deletion failed: {e}")

    def delete_relationships_by_type(
        self, project_id: str, relationship_types: list[str] | None = None
    ) -> int:
        """Delete relationships of specific type(s) for a project.

        Args:
            project_id: Project UUID
            relationship_types: List of relationship types to delete
                               (e.g., ['CALLS', 'DEPENDS_ON']). If None, deletes all.

        Returns:
            Number of deleted relationships

        Raises:
            GraphStorageError: If deletion fails
        """
        try:
            with self.connection_manager.transaction() as tx:
                if relationship_types:
                    # Build query for specific types
                    type_list = "|".join([f"`{t}`" for t in relationship_types])
                    query = f"""
                        MATCH ()-[r:{type_list} {{project_id: $project_id}}]->()
                        DELETE r
                        RETURN count(r) as deleted_count
                    """
                else:
                    # Delete all relationships
                    query = self.CYPHER_DELETE_RELATIONSHIPS

                params = {"project_id": project_id}
                result = tx.run(query, params)
                record = result.single()
                count = record["deleted_count"] if record else 0

                logger.info(
                    f"Deleted {count} relationships of type(s) "
                    f'{relationship_types or "all"} for project {project_id}'
                )
                return count

        except Exception as e:
            logger.error(f"Failed to delete relationships by type: {e}")
            raise GraphStorageError(f"Type-based relationship deletion failed: {e}")
