#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
DEPLOY_ENV="${1:-}"
case "$DEPLOY_ENV" in
    test | prod)
        ENV_FILE=".env.$DEPLOY_ENV"
        ;;
    *)
        echo "用法：$0 test|prod" >&2
        echo "错误：必须明确指定运行环境，防止定时任务读取错误的 Nacos 配置。" >&2
        exit 2
        ;;
esac

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
    echo "[$(date '+%F %T')] cron 政策材料同步任务启动，环境：$DEPLOY_ENV，配置：$ENV_PATH"
    /usr/bin/bash "$SCRIPT_DIR/run_policy_sync.sh"
    echo "[$(date '+%F %T')] cron 政策材料同步任务结束"
} >>"$LOG_FILE" 2>&1
