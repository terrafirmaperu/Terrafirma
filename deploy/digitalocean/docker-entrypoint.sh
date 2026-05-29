#!/usr/bin/env bash
set -euo pipefail
# Jobs de App Platform (python manage.py …) deben ejecutarse sin paso extra.
if [ "${1:-}" = "python" ]; then
  exec "$@"
fi
if [ "${RUN_MIGRATE:-0}" = "1" ]; then
  python manage.py migrate --noinput
fi
exec "$@"
