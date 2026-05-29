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

if [ "${RUN_BOOTSTRAP:-0}" = "1" ]; then
  echo "==> bootstrap_production"
  python manage.py bootstrap_production --seed --skip-static
fi

if [ -n "${NEO_ADMIN_PASSWORD:-}" ]; then
  echo "==> ensure_neo_superuser"
  python manage.py ensure_neo_superuser --password "$NEO_ADMIN_PASSWORD"
fi

exec "$@"
