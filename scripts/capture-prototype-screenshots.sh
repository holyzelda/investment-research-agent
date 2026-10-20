#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
image="investment-research-agent/prototype-screenshots:playwright-1.48.2"

if ! command -v docker >/dev/null 2>&1; then
  printf 'error: Docker is required to create the isolated screenshot environment\n' >&2
  exit 1
fi

docker build \
  --tag "$image" \
  "$repo_root/tools/prototype-screenshots"

docker run --rm \
  --init \
  --user "$(id -u):$(id -g)" \
  --env HOME=/tmp \
  --volume "$repo_root:/workspace" \
  "$image"
