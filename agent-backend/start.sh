#!/usr/bin/env bash
# CI/CD 后端服务启动脚本。

set -euo pipefail

# 脚本可从仓库任意目录调用，所有相对路径均以 agent-backend 为基准。
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

ENV_FILE="${ENV_FILE:-.env.test}"
if [[ "$ENV_FILE" = /* ]]; then
    ENV_PATH="$ENV_FILE"
else
    ENV_PATH="$SCRIPT_DIR/$ENV_FILE"
fi

PID_FILE="$SCRIPT_DIR/logs/app.pid"
LOG_FILE="$SCRIPT_DIR/logs/app.log"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date '+%H:%M:%S')] ✔ $*${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date '+%H:%M:%S')] ⚠ $*${NC}"
}

fail() {
    echo -e "${RED}[$(date '+%H:%M:%S')] ✘ $*${NC}" >&2
    exit 1
}

log "加载环境文件: $ENV_PATH"
if [[ -f "$ENV_PATH" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "$ENV_PATH" || fail "加载环境文件失败: $ENV_PATH"
    set +a
else
    warn "未找到 $ENV_PATH，使用默认配置"
fi

HOST="${APP_HOST:-0.0.0.0}"
PORT="${APP_PORT:-9089}"
WORKERS="${APP_WORKERS:-2}"
HEALTH_URL="http://127.0.0.1:${PORT}/health"

if [[ -x "$SCRIPT_DIR/.venv/bin/python" ]]; then
    PYTHON="$SCRIPT_DIR/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON="$(command -v python3)"
elif command -v python >/dev/null 2>&1; then
    PYTHON="$(command -v python)"
else
    fail "未找到 Python，请确认已创建 .venv 或安装 Python"
fi

log "Python 版本: $($PYTHON --version)"

[[ -f requirements.txt ]] || fail "未找到 requirements.txt"
log "安装依赖"
"$PYTHON" -m pip install -r requirements.txt || fail "依赖安装失败"

mkdir -p "$SCRIPT_DIR/logs" || fail "无法创建日志目录"

if [[ -f "$PID_FILE" ]]; then
    read -r OLD_PID < "$PID_FILE" || OLD_PID=""
    if [[ "$OLD_PID" =~ ^[0-9]+$ ]] && kill -0 "$OLD_PID" 2>/dev/null; then
        warn "停止旧进程 PID=$OLD_PID"
        kill -TERM "$OLD_PID" 2>/dev/null || true
        for _ in $(seq 1 10); do
            kill -0 "$OLD_PID" 2>/dev/null || break
            sleep 1
        done
        if kill -0 "$OLD_PID" 2>/dev/null; then
            kill -KILL "$OLD_PID" 2>/dev/null || true
        fi
    fi
    rm -f "$PID_FILE"
fi

log "启动服务: ${HOST}:${PORT}（workers=${WORKERS}）"
APP_ENV="$ENV_FILE" APP_HOST="$HOST" APP_PORT="$PORT" \
    nohup "$PYTHON" -m uvicorn app.main:app \
    --host "$HOST" \
    --port "$PORT" \
    --workers "$WORKERS" \
    >> "$LOG_FILE" 2>&1 &
NEW_PID=$!
echo "$NEW_PID" > "$PID_FILE"

sleep 1
if ! kill -0 "$NEW_PID" 2>/dev/null; then
    rm -f "$PID_FILE"
    fail "服务进程启动后立即退出（PID=$NEW_PID），请查看日志: $LOG_FILE"
fi
log "服务已启动 PID=$NEW_PID"

log "健康检查: $HEALTH_URL"
for i in $(seq 1 8); do
    CODE="$(curl -s -o /dev/null -w '%{http_code}' --max-time 3 "$HEALTH_URL" 2>/dev/null || echo 000)"
    if [[ "$CODE" = "200" ]]; then
        log "健康检查通过 (HTTP 200)"
        break
    fi
    warn "等待服务就绪... ($i/8) HTTP=$CODE"
    [[ "$i" -eq 8 ]] && fail "服务未就绪，请查看日志: $LOG_FILE"
    sleep 3
done

echo -e "${GREEN}部署完成: http://$HOST:$PORT [$ENV_FILE]${NC}"
echo -e "${GREEN}日志: $LOG_FILE${NC}"
