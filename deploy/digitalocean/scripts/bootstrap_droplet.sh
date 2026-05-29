#!/usr/bin/env bash
# Instalación inicial en Ubuntu 22.04/24.04 (Droplet). Ejecutar como root o con sudo.
set -euo pipefail

APP_USER="${APP_USER:-www-data}"
APP_ROOT="${APP_ROOT:-/var/www/terrafirma}"
APP_DIR="${APP_DIR:-${APP_ROOT}/app}"
DOMAIN="${DOMAIN:-terrafirmaperu.com}"

export DEBIAN_FRONTEND=noninteractive

apt-get update
apt-get install -y python3 python3-venv python3-pip nginx certbot python3-certbot-nginx \
  libpq-dev build-essential \
  libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libffi-dev shared-mime-info

mkdir -p "$APP_ROOT" "$APP_DIR" "${APP_DIR}/logs" "${APP_DIR}/db" "${APP_DIR}/media"
chown -R "${APP_USER}:${APP_USER}" "$APP_ROOT"

if [ ! -d "${APP_DIR}/venv" ]; then
  python3 -m venv "${APP_DIR}/venv"
fi

# El código debe estar ya en APP_DIR (git clone / rsync)
if [ -f "${APP_DIR}/requirements.txt" ]; then
  sudo -u "$APP_USER" bash -c "
    source '${APP_DIR}/venv/bin/activate'
    pip install --upgrade pip
    pip install -r '${APP_DIR}/requirements.txt'
  "
fi

if [ ! -f "${APP_DIR}/.env" ] && [ -f "${APP_DIR}/deploy/digitalocean/env.example" ]; then
  cp "${APP_DIR}/deploy/digitalocean/env.example" "${APP_DIR}/.env"
  chown "${APP_USER}:${APP_USER}" "${APP_DIR}/.env"
  echo 'Edite ${APP_DIR}/.env antes de continuar.'
fi

install -m 644 "${APP_DIR}/deploy/digitalocean/nginx/terrafirma.conf" /etc/nginx/sites-available/terrafirma
ln -sf /etc/nginx/sites-available/terrafirma /etc/nginx/sites-enabled/terrafirma
rm -f /etc/nginx/sites-enabled/default
nginx -t

install -m 644 "${APP_DIR}/deploy/digitalocean/systemd/terrafirma.service" /etc/systemd/system/terrafirma.service
systemctl daemon-reload

echo ""
echo "Siguiente (como ${APP_USER}, con .env configurado):"
echo "  cd ${APP_DIR} && source venv/bin/activate"
echo "  set -a && source .env && set +a"
echo "  python manage.py bootstrap_production --seed"
echo "  sudo systemctl enable --now terrafirma"
echo "  sudo systemctl reload nginx"
echo "  sudo certbot --nginx -d ${DOMAIN} -d www.${DOMAIN}"
