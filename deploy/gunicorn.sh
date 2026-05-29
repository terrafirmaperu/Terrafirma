#!/usr/bin/env bash
# Arranque Gunicorn (Droplet). Ajuste APP_DIR y copie a systemd o supervisor.
set -euo pipefail

APP_DIR="${APP_DIR:-/var/www/terrafirma/app}"
VENV="${VENV:-${APP_DIR}/venv}"
SOCKFILE="${GUNICORN_SOCKET:-/run/terrafirma/gunicorn.sock}"
LOGDIR="${APP_DIR}/logs"
NUM_WORKERS="${GUNICORN_WORKERS:-3}"
TIMEOUT="${GUNICORN_TIMEOUT:-120}"

export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-config.production}"

mkdir -p "$(dirname "$SOCKFILE")" "$LOGDIR"
rm -f "$SOCKFILE"

cd "$APP_DIR"
source "${VENV}/bin/activate"

exec gunicorn config.wsgi:application \
  --name terrafirma \
  --workers "$NUM_WORKERS" \
  --timeout "$TIMEOUT" \
  --bind "unix:${SOCKFILE}" \
  --access-logfile "${LOGDIR}/gunicorn-access.log" \
  --error-logfile "${LOGDIR}/gunicorn-error.log" \
  --log-level info
