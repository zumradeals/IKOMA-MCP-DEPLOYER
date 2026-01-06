#!/usr/bin/env bash
set -euo pipefail

UVICORN_CMD=${UVICORN_CMD:-uvicorn}
PORT=${PORT:-8088}
HOST=${HOST:-0.0.0.0}

exec ${UVICORN_CMD} runner.app:app --host "${HOST}" --port "${PORT}"
