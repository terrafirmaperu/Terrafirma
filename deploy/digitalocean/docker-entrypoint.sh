#!/usr/bin/env bash
set -euo pipefail

# Job PRE_DEPLOY: sh -c "python manage.py migrate --noinput"
if [ "${1:-}" = "sh" ] && [ "${2:-}" = "-c" ] && [[ "${3:-}" == *manage.py* ]]; then
  exec "$@"
fi

if [ "${RUN_MIGRATE:-0}" = "1" ]; then
  echo "==> migrate"
  python manage.py migrate --noinput
fi

exec "$@"
