#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
COMPOSE_FILE="${SCRIPT_DIR}/docker-compose.yml"
STATE_FILE="${SCRIPT_DIR}/.backend-image.hash"

find_compose_runner() {
  if command -v podman-compose >/dev/null 2>&1; then
    printf 'podman-compose'
    return 0
  fi

  if command -v podman >/dev/null 2>&1; then
    printf 'podman compose'
    return 0
  fi

  if command -v docker >/dev/null 2>&1; then
    printf 'docker compose'
    return 0
  fi

  echo "No supported compose runner found. Install podman-compose, podman, or docker." >&2
  exit 1
}

compute_hash() {
  (
    cd "${REPO_ROOT}"
    python3 - <<'PY'
from hashlib import sha256
from pathlib import Path

repo_root = Path.cwd()
targets = [
    repo_root / "docker" / "Dockerfile",
    repo_root / "docker" / "wait_for_neo4j.py",
    repo_root / "requirements.txt",
]
targets.extend(
    path for path in sorted((repo_root / "codeminer").rglob("*"))
    if path.is_file() and "__pycache__" not in path.parts and path.suffix not in {".pyc", ".pyo"}
)

digest = sha256()
for path in targets:
    digest.update(str(path.relative_to(repo_root)).encode("utf-8"))
    digest.update(b"\0")
    digest.update(path.read_bytes())
    digest.update(b"\0")

print(digest.hexdigest())
PY
  )
}

NEW_HASH="$(compute_hash)"
OLD_HASH=""
COMPOSE_RUNNER="$(find_compose_runner)"

if [[ -f "${STATE_FILE}" ]]; then
  OLD_HASH="$(<"${STATE_FILE}")"
fi

if [[ "${NEW_HASH}" == "${OLD_HASH}" ]]; then
  echo "No backend source changes detected. Image rebuild skipped."
  exit 0
fi

echo "Backend source changes detected. Rebuilding backend image with: ${COMPOSE_RUNNER}"
${COMPOSE_RUNNER} -f "${COMPOSE_FILE}" build backend
${COMPOSE_RUNNER} -f "${COMPOSE_FILE}" up -d backend

printf '%s\n' "${NEW_HASH}" > "${STATE_FILE}"
echo "Backend image updated and backend service restarted."
