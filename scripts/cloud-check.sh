#!/usr/bin/env bash
set -uo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export NACOS_ENABLED=false
export IR_FEISHU_ENABLED=false
export IR_SPOT_ENABLED=false
export IR_SPOT_DAILY_UPDATE_ENABLED=false
export IR_DB_URL='sqlite+aiosqlite:///:memory:'

names=()
codes=()

run_check() {
  local name="$1"
  shift
  printf '\n===== %s =====\n' "$name"
  "$@"
  local code=$?
  names+=("$name")
  codes+=("$code")
}

run_check 'backend unit tests' \
  bash -c 'cd "$1" && exec .venv/bin/python -m pytest tests/unit -q' _ "$repo_root/agent-backend"
run_check 'frontend tests' npm --prefix "$repo_root/agent-frontend" test
run_check 'frontend build' npm --prefix "$repo_root/agent-frontend" run build

printf '\n===== exit-code summary =====\n'
overall=0
for i in "${!names[@]}"; do
  printf '%s: %s\n' "${names[$i]}" "${codes[$i]}"
  if (( codes[i] != 0 )); then
    overall=1
  fi
done
exit "$overall"
