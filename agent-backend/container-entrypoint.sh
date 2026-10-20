#!/bin/sh
set -eu

: "${IR_DB_URL:?IR_DB_URL must be supplied by the approved environment}"
APP_CORS_ALLOW_CREDENTIALS="${APP_CORS_ALLOW_CREDENTIALS:-false}"
export APP_CORS_ALLOW_CREDENTIALS

exec python -m uvicorn app.main:app --host 0.0.0.0 --port "${APP_PORT:-9089}"
