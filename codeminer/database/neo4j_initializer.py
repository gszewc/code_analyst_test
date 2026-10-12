"""
Neo4j Schema Initializer.

Provides schema initialization and verification for Neo4j database,
including indexes, constraints, and schema validation.
"""

import logging
from typing import Dict, Any

from neo4j.exceptions import CypherSyntaxError, ClientError

from .neo4j_manager import Neo4jConnectionManager

logger = logging.getLogger(__name__)


# Schema version for tracking
SCHEMA_VERSION = 2

# Individual index creation statements (one per session.run() call)
CONSTRAINT_STATEMENTS = [
    # Unique constraint for ASTNode id (also provides index lookups on n.id)
    "CREATE CONSTRAINT ast_node_unique_id IF NOT EXISTS FOR (n:ASTNode) REQUIRE n.id IS UNIQUE",
]

# Drop the standalone id index if it exists — the unique constraint provides this
PRE_INDEX_CLEANUP = [
    "DROP INDEX ast_node_id IF EXISTS",
]

INDEX_STATEMENTS = [
    # Index for project_id lookups (most common query pattern)
    "CREATE INDEX ast_node_project_id IF NOT EXISTS FOR (n:ASTNode) ON (n.project_id)",
    # Index for node type filtering
    "CREATE INDEX ast_node_type IF NOT EXISTS FOR (n:ASTNode) ON (n.type)",
    # Index for source file lookups
    "CREATE INDEX ast_node_source_file IF NOT EXISTS FOR (n:ASTNode) ON (n.source_file)",
    # Index for language filtering
    "CREATE INDEX ast_node_language IF NOT EXISTS FOR (n:ASTNode) ON (n.language)",
    # Indexes for relationship project lookups (one per relationship type)
    "CREATE INDEX rel_contains_project_id IF NOT EXISTS FOR ()-[r:CONTAINS]-() ON (r.project_id)",
    "CREATE INDEX rel_extends_project_id IF NOT EXISTS FOR ()-[r:EXTENDS]-() ON (r.project_id)",
    "CREATE INDEX rel_implements_project_id IF NOT EXISTS FOR ()-[r:IMPLEMENTS]-() ON (r.project_id)",
    "CREATE INDEX rel_calls_project_id IF NOT EXISTS FOR ()-[r:CALLS]-() ON (r.project_id)",
    "CREATE INDEX rel_depends_on_project_id IF NOT EXISTS FOR ()-[r:DEPENDS_ON]-() ON (r.project_id)",
    "CREATE INDEX rel_uses_project_id IF NOT EXISTS FOR ()-[r:USES]-() ON (r.project_id)",
]

SCHEMA_VERSION_CYPHER = """
MERGE (s:SchemaVersion {version: $version})
ON CREATE SET s.applied_at = datetime()
ON MATCH SET s.updated_at = datetime()
RETURN s.version
"""

VERIFY_SCHEMA_CYPHER = """
MATCH (s:SchemaVersion {version: $version})
RETURN s.version IS NOT NULL as exists
"""


class Neo4jInitError(Exception):
    """Exception raised for Neo4j initialization errors."""
    pass


class Neo4jInitializer:
    """Neo4j schema initialization.

    Initializes and verifies Neo4j schema including indexes,
    constraints, and schema version tracking.

    Example:
        >>> neo4j_manager = Neo4jConnectionManager(config)
        >>> Neo4jInitializer.init_schema(neo4j_manager)
        >>> assert Neo4jInitializer.verify_schema(neo4j_manager)
    """

    @staticmethod
    def init_schema(connection_manager: Neo4jConnectionManager) -> None:
        """Initialize Neo4j schema.

        Creates indexes and constraints if they don't exist.
        Records schema version.

        Args:
            connection_manager: Neo4j connection manager instance

        Raises:
            Neo4jInitError: If schema initialization fails
        """
        try:
            logger.info('Initializing Neo4j schema')

            with connection_manager.get_session() as session:
                # Drop legacy indexes that conflict with constraints
                logger.debug('Cleaning up legacy indexes')
                for stmt in PRE_INDEX_CLEANUP:
                    session.run(stmt)

                # Create constraints first (unique constraint on id provides index)
                logger.debug('Creating constraints')
                for stmt in CONSTRAINT_STATEMENTS:
                    session.run(stmt)

                # Create indexes (one statement per run)
                logger.debug('Creating indexes')
                for stmt in INDEX_STATEMENTS:
                    session.run(stmt)

                # Record schema version
                logger.debug('Recording schema version')
                session.run(SCHEMA_VERSION_CYPHER, {'version': SCHEMA_VERSION})

            logger.info(f'Neo4j schema initialized (version {SCHEMA_VERSION})')

        except CypherSyntaxError as e:
            logger.error(f'Cypher syntax error: {e}')
            raise Neo4jInitError(f'Invalid Cypher: {e}')
        except ClientError as e:
            logger.error(f'Neo4j client error: {e}')
            raise Neo4jInitError(f'Client error: {e}')
        except Exception as e:
            logger.error(f'Schema initialization failed: {e}')
            raise Neo4jInitError(f'Failed to initialize schema: {e}')

    @staticmethod
    def verify_schema(connection_manager: Neo4jConnectionManager) -> bool:
        """Verify Neo4j schema integrity.

        Checks that required indexes and constraints exist.

        Args:
            connection_manager: Neo4j connection manager instance

        Returns:
            True if schema is valid, False otherwise
        """
        try:
            with connection_manager.get_session() as session:
                # Check schema version
                result = session.run(VERIFY_SCHEMA_CYPHER, {'version': SCHEMA_VERSION})
                record = result.single()

                if record is None or not record['exists']:
                    logger.warning(f'Schema version {SCHEMA_VERSION} not found')
                    return False

                # Check required indexes
                required_indexes = {
                    'ast_node_project_id',
                    'ast_node_type',
                    'ast_node_source_file',
                    'ast_node_language',
                    'rel_contains_project_id',
                    'rel_extends_project_id',
                    'rel_implements_project_id',
                    'rel_calls_project_id',
                    'rel_depends_on_project_id',
                    'rel_uses_project_id',
                }

                index_result = session.run("""
                    SHOW INDEXES
                    WHERE type = 'RANGE'
                    RETURN name
                """)
                existing_indexes = set(row['name'] for row in index_result)

                if not required_indexes.issubset(existing_indexes):
                    missing = required_indexes - existing_indexes
                    logger.warning(f'Missing indexes: {missing}')
                    return False

                # Check required constraints
                constraint_result = session.run("""
                    SHOW CONSTRAINTS
                    WHERE type = 'UNIQUENESS'
                    RETURN name
                """)
                existing_constraints = set(row['name'] for row in constraint_result)

                required_constraints = {'ast_node_unique_id'}
                if not required_constraints.issubset(existing_constraints):
                    missing = required_constraints - existing_constraints
                    logger.warning(f'Missing constraints: {missing}')
                    return False

            logger.info('Neo4j schema verified successfully')
            return True

        except Exception as e:
            logger.error(f'Schema verification failed: {e}')
            return False

    @staticmethod
    def get_schema_info(connection_manager: Neo4jConnectionManager) -> Dict[str, Any]:
        """Get schema information.

        Args:
            connection_manager: Neo4j connection manager instance

        Returns:
            Dictionary with schema information
        """
        try:
            with connection_manager.get_session() as session:
                # Get indexes
                index_result = session.run("""
                    SHOW INDEXES
                    WHERE type = 'RANGE'
                    RETURN name, labelsOrTypes, properties
                """)
                indexes = [
                    {
                        'name': row['name'],
                        'labels': row['labelsOrTypes'],
                        'properties': row['properties']
                    }
                    for row in index_result
                ]

                # Get constraints
                constraint_result = session.run("""
                    SHOW CONSTRAINTS
                    RETURN name, type, labelsOrTypes, properties
                """)
                constraints = [
                    {
                        'name': row['name'],
                        'type': row['type'],
                        'labels': row['labelsOrTypes'],
                        'properties': row['properties']
                    }
                    for row in constraint_result
                ]

                # Get schema version
                version_result = session.run(
                    'MATCH (s:SchemaVersion) RETURN s.version ORDER BY s.version DESC LIMIT 1'
                )
                version_record = version_result.single()
                schema_version = version_record['s.version'] if version_record else 0

                # Get node label counts
                label_result = session.run("""
                    CALL db.labels()
                    YIELD label
                    MATCH (n)
                    WHERE label IN labels(n)
                    RETURN label, count(n) as count
                """)
                node_counts = {
                    row['label']: row['count']
                    for row in label_result
                }

                # Get relationship type counts
                rel_result = session.run("""
                    CALL db.relationshipTypes()
                    YIELD relationshipType
                    MATCH ()-[r]->()
                    WHERE type(r) = relationshipType
                    RETURN relationshipType, count(r) as count
                """)
                rel_counts = {
                    row['relationshipType']: row['count']
                    for row in rel_result
                }

                return {
                    'version': schema_version,
                    'indexes': indexes,
                    'constraints': constraints,
                    'node_counts': node_counts,
                    'relationship_counts': rel_counts
                }

        except Exception as e:
            logger.error(f'Failed to get schema info: {e}')
            return {
                'version': 0,
                'indexes': [],
                'constraints': [],
                'node_counts': {},
                'relationship_counts': {}
            }
