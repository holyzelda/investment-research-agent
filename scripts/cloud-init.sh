#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

python_bin="${PYTHON_BIN:-python3.13}"
if ! command -v "$python_bin" >/dev/null 2>&1; then
  printf 'error: Python 3.13 is required (set PYTHON_BIN to its executable)\n' >&2
  exit 1
fi
if [[ "$($python_bin -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')" != "3.13" ]]; then
  printf 'error: %s is not Python 3.13\n' "$python_bin" >&2
  exit 1
fi
if ! command -v node >/dev/null 2>&1 || [[ "$(node -p 'process.versions.node.split(".")[0]')" != "22" ]]; then
  printf 'error: Node.js 22 is required (see .nvmrc)\n' >&2
  exit 1
fi

"$python_bin" -m venv "$repo_root/agent-backend/.venv"
"$repo_root/agent-backend/.venv/bin/python" -m pip install -r "$repo_root/agent-backend/requirements.txt"
npm --prefix "$repo_root/agent-frontend" ci
