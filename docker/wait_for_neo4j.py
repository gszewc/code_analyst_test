"""Wait for Neo4j readiness before starting the backend container."""

from __future__ import annotations

import os
import sys
import time

from neo4j import GraphDatabase


def main() -> int:
    uri = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "password")
    timeout_seconds = int(os.getenv("NEO4J_STARTUP_TIMEOUT", "90"))
    retry_delay = float(os.getenv("NEO4J_STARTUP_RETRY_DELAY", "2"))

    deadline = time.monotonic() + timeout_seconds
    attempt = 1

    while time.monotonic() < deadline:
        try:
            driver = GraphDatabase.driver(uri, auth=(user, password))
            driver.verify_connectivity()
            driver.close()
            print(f"Neo4j is ready at {uri}")
            return 0
        except Exception as exc:
            remaining = max(0, int(deadline - time.monotonic()))
            print(
                f"Waiting for Neo4j at {uri} (attempt {attempt}, {remaining}s remaining): {exc}",
                file=sys.stderr,
            )
            attempt += 1
            time.sleep(retry_delay)

    print(f"Timed out waiting for Neo4j at {uri}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
