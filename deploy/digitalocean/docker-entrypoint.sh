#!/usr/bin/env bash
set -euo pipefail
if [ "${RUN_MIGRATE:-0}" = "1" ]; then
  python manage.py migrate --noinput || {
    echo "migrate failed (exit $?)" >&2
    exit 1
  }
fi
exec "$@"
