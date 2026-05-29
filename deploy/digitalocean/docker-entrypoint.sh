#!/usr/bin/env bash
set -euo pipefail
echo "==> DJANGO_SETTINGS_MODULE=${DJANGO_SETTINGS_MODULE:-}"
echo "==> DATABASE_URL set: $([ -n \"${DATABASE_URL:-}\" ] && echo yes || echo no)"
if [ "${SKIP_MIGRATE:-0}" != "1" ]; then
  echo "==> migrate"
  python manage.py migrate --noinput --verbosity 2
fi
echo "==> check"
python manage.py check
echo "==> start: $*"
exec "$@"
