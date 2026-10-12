// Migration: Backfill language field on existing ASTNode nodes
// Date: 2026-03-26
// Description: Sets language="python" on all ASTNode nodes where the language
//              field is missing or empty. This covers nodes created before the
//              multi-language parsing feature was introduced.
//
// Prerequisites:
//   - Neo4j 4.4+ (for IF NOT EXISTS syntax)
//
// Usage:
//   Run each statement separately in the Neo4j Browser or cypher-shell:
//
//     cat migrations/neo4j/001_backfill_language_python.cypher | cypher-shell -u neo4j -p <password>
//
//   Or paste individual statements into the Neo4j Browser.
//
// Safety:
//   - Idempotent: safe to run multiple times
//   - Uses CALL IN TRANSACTIONS to avoid large heap usage on big datasets

// Step 1: Create the language index (if not already created by app startup)
CREATE INDEX ast_node_language IF NOT EXISTS FOR (n:ASTNode) ON (n.language);

// Step 2: Backfill language="python" on nodes with empty or missing language field
// Uses batched transactions (500 nodes at a time) to keep memory usage low
CALL {
  MATCH (n:ASTNode)
  WHERE n.language IS NULL OR n.language = ""
  SET n.language = "python"
} IN TRANSACTIONS OF 500 ROWS;

// Step 3: Verify — count remaining nodes without a language
MATCH (n:ASTNode) WHERE n.language IS NULL OR n.language = ""
RETURN count(n) AS nodes_without_language;
