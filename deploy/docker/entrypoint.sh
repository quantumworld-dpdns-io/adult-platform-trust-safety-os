#!/bin/sh
set -e

echo "==> Adult Platform Trust & Safety OS - Entrypoint"

echo "==> Running database migrations..."
alembic upgrade head || {
    echo "WARNING: Alembic migration failed or not configured, skipping"
}

echo "==> Starting API server..."
exec uvicorn src.api.app:app \
    --host "${APP_HOST:-0.0.0.0}" \
    --port "${APP_PORT:-8000}" \
    --workers "${WORKERS:-2}" \
    --log-level "${LOG_LEVEL:-info}" \
    --proxy-headers \
    --forwarded-allow-ips='*' \
    --access-log
