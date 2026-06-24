#!/bin/sh
set -e

PORT="${API_PAC_QUALITY_PORT:-8010}"
ROOT_PATH="${API_PAC_ROOT_PATH:-}"

if [ -n "$ROOT_PATH" ] && [ "$ROOT_PATH" != "/" ]; then
  exec python -m uvicorn app.asgi:application \
    --host 0.0.0.0 \
    --port "$PORT" \
    --root-path "$ROOT_PATH"
fi

exec python -m uvicorn app.asgi:application \
  --host 0.0.0.0 \
  --port "$PORT"
