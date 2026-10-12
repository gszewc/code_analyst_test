#!/usr/bin/env bash
# start.sh - Starts backend (codeminer) or frontend in a local environment.
#
# Usage:
#   scripts/start.sh backend    # checks/starts Neo4j, then runs uvicorn
#   scripts/start.sh frontend   # runs Vite dev server
#
# The script must be run from the repository root directory.

set -euo pipefail

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

REPO_ROOT="$(git rev-parse --show-toplevel)"
COMPOSE_FILE="${REPO_ROOT}/docker/docker-compose.yml"
NEO4J_CONTAINER="code_analyst_neo4j"
NEO4J_SERVICE="neo4j"
NEO4J_HEALTHY_TIMEOUT=120   # seconds to wait for healthy status
VENV_ACTIVATE="${REPO_ROOT}/.venv/bin/activate"
ENV_FILE="${REPO_ROOT}/.env"

log()  { echo "[start.sh] $*"; }
err()  { echo "[start.sh] ERROR: $*" >&2; exit 1; }

# Detect compose tool
detect_compose() {
    if command -v podman-compose &>/dev/null; then
        echo "podman-compose"
    elif podman compose version &>/dev/null 2>&1; then
        echo "podman compose"
    elif command -v docker &>/dev/null && docker compose version &>/dev/null 2>&1; then
        echo "docker compose"
    else
        err "Could not find podman-compose, 'podman compose', or 'docker compose'."
    fi
}

# Returns 0 if the container is running (status = running)
container_running() {
    local name="$1"
    # podman and docker use the same inspect format
    local state
    state=$(podman inspect --format '{{.State.Status}}' "${name}" 2>/dev/null || true)
    [[ "${state}" == "running" ]]
}

# Waits until the container reaches healthy status
wait_for_healthy() {
    local name="$1"
    local timeout="$2"
    local elapsed=0
    local interval=5

    log "Waiting for container '${name}' to reach 'healthy' status (max ${timeout}s)..."
    while [[ ${elapsed} -lt ${timeout} ]]; do
        local health
        health=$(podman inspect --format '{{.State.Health.Status}}' "${name}" 2>/dev/null || true)
        if [[ "${health}" == "healthy" ]]; then
            log "Container '${name}' is healthy."
            return 0
        fi
        sleep "${interval}"
        elapsed=$(( elapsed + interval ))
        log "  ...${elapsed}s / ${timeout}s (status: ${health:-unknown})"
    done

    err "Container '${name}' did not reach healthy status within ${timeout}s."
}

# ---------------------------------------------------------------------------
# Mode: backend
# ---------------------------------------------------------------------------

start_backend() {
    local compose_cmd
    compose_cmd="$(detect_compose)"
    log "Compose tool: ${compose_cmd}"

    # Check/start Neo4j
    if container_running "${NEO4J_CONTAINER}"; then
        log "Container '${NEO4J_CONTAINER}' is already running."
    else
        log "Container '${NEO4J_CONTAINER}' is not running. Starting service '${NEO4J_SERVICE}'..."
        ${compose_cmd} -f "${COMPOSE_FILE}" up -d "${NEO4J_SERVICE}"
    fi

    wait_for_healthy "${NEO4J_CONTAINER}" "${NEO4J_HEALTHY_TIMEOUT}"

    # Load environment variables
    if [[ -f "${ENV_FILE}" ]]; then
        log "Loading variables from ${ENV_FILE}"
        # shellcheck source=/dev/null
        set -o allexport
        source "${ENV_FILE}"
        set +o allexport
    else
        log "No .env file found - using default settings."
    fi

    # Activate venv
    if [[ ! -f "${VENV_ACTIVATE}" ]]; then
        err "Virtualenv not found: ${VENV_ACTIVATE}. Run: python3 -m venv venv && pip install -r requirements.txt"
    fi
    log "Activating virtualenv: ${VENV_ACTIVATE}"
    # shellcheck source=/dev/null
    source "${VENV_ACTIVATE}"

    log "Starting backend (uvicorn) with hot reload..."
    cd "${REPO_ROOT}"
    exec uvicorn codeminer.api.main:app \
        --reload \
        --host "${API_HOST:-0.0.0.0}" \
        --port "${API_PORT:-8080}"
}

# ---------------------------------------------------------------------------
# Mode: frontend
# ---------------------------------------------------------------------------

start_frontend() {
    local frontend_dir="${REPO_ROOT}/frontend"

    if [[ ! -d "${frontend_dir}/node_modules" ]]; then
        log "node_modules directory does not exist. Installing dependencies (npm ci)..."
        npm ci --prefix "${frontend_dir}"
    fi

    log "Starting frontend (Vite dev server) at http://localhost:3000..."
    cd "${frontend_dir}"
    exec npm run dev
}

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

usage() {
    echo "Usage: $0 <backend|frontend>" >&2
    exit 1
}

if [[ $# -lt 1 ]]; then
    usage
fi

case "$1" in
    backend)  start_backend ;;
    frontend) start_frontend ;;
    *)        usage ;;
esac
