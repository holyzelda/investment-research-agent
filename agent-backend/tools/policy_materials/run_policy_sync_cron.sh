#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
ENV_FILE="${ENV_FILE:-.env.prod}"
if [[ "$ENV_FILE" = /* ]]; then
    ENV_PATH="$ENV_FILE"
else
    ENV_PATH="$PROJECT_DIR/$ENV_FILE"
fi

if [[ ! -r "$ENV_PATH" ]]; then
    echo "错误：任务环境配置不存在或不可读：$ENV_PATH" >&2
    exit 1
fi

set -a
# shellcheck disable=SC1090
source "$ENV_PATH"
set +a

LOG_DIR="${POLICY_LOG_DIR:-$PROJECT_DIR/data/policy_materials/logs}"
LOG_FILE="$LOG_DIR/policy-sync-$(date +%Y-%m).log"
mkdir -p "$LOG_DIR"

on_exit() {
    local status=$?
    if [[ "$status" -ne 0 ]]; then
        echo "[$(date '+%F %T')] cron 政策材料同步任务失败，退出码：$status" >>"$LOG_FILE"
    fi
}
trap on_exit EXIT

{
    echo "[$(date '+%F %T')] cron 政策材料同步任务启动"
    /usr/bin/bash "$SCRIPT_DIR/run_policy_sync.sh"
    echo "[$(date '+%F %T')] cron 政策材料同步任务结束"
} >>"$LOG_FILE" 2>&1
