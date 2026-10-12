#!/usr/bin/env bash
# new-worktree.sh — Creates a new git worktree with a ready-to-use Python environment.
#
# Usage: scripts/new-worktree.sh <branch-name>
#
# The script must be run from the repository root.

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
WORKTREES_DIR="${REPO_ROOT}/.worktrees"

# --- Validate input -------------------------------------------------------

if [[ $# -lt 1 ]]; then
    echo "Usage: $0 <branch-name>" >&2
    exit 1
fi

BRANCH_NAME="$1"
WORKTREE_DIR="${WORKTREES_DIR}/${BRANCH_NAME}"

if [[ -d "${WORKTREE_DIR}" ]]; then
    echo "Error: worktree directory already exists: ${WORKTREE_DIR}" >&2
    exit 1
fi

# --- Step 1: Create worktree ----------------------------------------------

echo "==> [1/5] Creating worktree '${BRANCH_NAME}' at ${WORKTREE_DIR}"
git -C "${REPO_ROOT}" worktree add -b "${BRANCH_NAME}" "${WORKTREE_DIR}"

# --- Step 2: Copy .env file -----------------------------------------------

echo "==> [2/5] Copying .env file"
if [[ -f "${REPO_ROOT}/.env" ]]; then
    cp "${REPO_ROOT}/.env" "${WORKTREE_DIR}/.env"
    echo "     Copied .env to ${WORKTREE_DIR}/.env"
else
    echo "     Warning: no .env file found in repo root — skipping copy" >&2
fi

# --- Step 3: Create virtual environment -----------------------------------

echo "==> [3/5] Creating Python virtual environment"
python3 -m venv "${WORKTREE_DIR}/.venv"

# --- Step 4: Install dependencies -----------------------------------------

echo "==> [4/5] Installing Python dependencies"
"${WORKTREE_DIR}/.venv/bin/pip" install --upgrade pip --quiet
"${WORKTREE_DIR}/.venv/bin/pip" install -r "${WORKTREE_DIR}/requirements.txt" --quiet

# --- Step 5: Run tests ----------------------------------------------------

echo "==> [5/5] Running pytest"
"${WORKTREE_DIR}/.venv/bin/pytest" --rootdir="${WORKTREE_DIR}" -c "${WORKTREE_DIR}/pytest.ini"

echo ""
echo "Done. Worktree ready at: ${WORKTREE_DIR}"
echo "Activate the environment with:"
echo "  source ${WORKTREE_DIR}/.venv/bin/activate"
