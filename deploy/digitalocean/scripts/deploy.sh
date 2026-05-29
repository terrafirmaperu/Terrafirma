#!/usr/bin/env bash
# Actualización tras git pull en el Droplet.
set -euo pipefail

APP_DIR="${APP_DIR:-/var/www/terrafirma/app}"
cd "$APP_DIR"

source venv/bin/activate
if [ -f .env ]; then
  set -a
  # shellcheck source=/dev/null
  source .env
  set +a
fi

export DJANGO_SETTINGS_MODULE=config.production

pip install -r requirements.txt
python manage.py migrate --noinput
python manage.py collectstatic --noinput
python manage.py bootstrap_production

sudo systemctl restart terrafirma
sudo systemctl reload nginx

echo "Deploy completado."
