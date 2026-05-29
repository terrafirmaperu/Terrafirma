#!/usr/bin/env bash
set -euo pipefail
if [ "${RUN_MIGRATE:-1}" = "1" ]; then
  python manage.py migrate --noinput
fi
exec "$@"
