#!/usr/bin/env python
"""Sincroniza produccion DO -> SQLite local (permisos.txt + .env.deploy + app-spec.local.yaml)."""
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_DIR))
os.chdir(APP_DIR)

DB_ID = 'ede94302-3bb1-4680-9f8c-90c89105c270'
APP_ID = '3107e7d7-80d9-4e46-a715-2485afc2d592'
SYNC_DIR = APP_DIR / 'db' / 'prod_parts'

CORE_PARTS = ['auth.group', 'user', 'security', 'whatsapp']
POS_MODELS = [
    'pos.company', 'pos.category', 'pos.product', 'pos.typeexpense',
    'pos.promotions', 'pos.promotionsdetail',
    'pos.clientcodecounter', 'pos.paymentconstanciacounter',
    'pos.client', 'pos.clientproperty',
    'pos.cashregistersession',
    'pos.collector',
    'pos.purchase', 'pos.purchasedetail',
    'pos.sale', 'pos.saledetail',
    'pos.ctascollect', 'pos.paymentsctacollect',
    'pos.debtspay', 'pos.paymentsdebtspay',
    'pos.expenses', 'pos.devolution',
    'pos.advisoryprogresscase', 'pos.advisoryprogressstage',
]

LOAD_ORDER = CORE_PARTS + POS_MODELS


def load_token():
    for line in (APP_DIR / '.env.deploy').read_text(encoding='utf-8').splitlines():
        if line.startswith('DIGITALOCEAN_ACCESS_TOKEN='):
            return line.split('=', 1)[1].strip()
    raise RuntimeError('Falta .env.deploy')


def read_spec_value(key):
    text = (APP_DIR / '.do' / 'app-spec.local.yaml').read_text(encoding='utf-8')
    block = re.search(rf'- key:\s*{re.escape(key)}\s*\n((?:\s+.+\n)+)', text)
    for line in block.group(1).splitlines():
        if line.strip().startswith('value:'):
            raw = line.strip().split(':', 1)[1].strip()
            return raw[1:-1] if raw.startswith('"') and raw.endswith('"') else raw
    raise RuntimeError(key)


def api(token, method, path, payload=None):
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    data = json.dumps(payload).encode() if payload else None
    req = urllib.request.Request(
        f'https://api.digitalocean.com/v2{path}', data=data, headers=headers, method=method,
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        body = resp.read().decode()
        return json.loads(body) if body else {}


def prod_env():
    return {
        'DJANGO_SETTINGS_MODULE': 'config.production',
        'DJANGO_ALLOWED_HOSTS': 'localhost',
        'DJANGO_SECRET_KEY': read_spec_value('DJANGO_SECRET_KEY'),
        'DATABASE_URL': read_spec_value('DATABASE_URL'),
        'PYTHONUTF8': '1',
        'PYTHONIOENCODING': 'utf-8',
    }


def local_env():
    env = os.environ.copy()
    for k in ('DATABASE_URL', 'DJANGO_SECRET_KEY', 'DJANGO_SETTINGS_MODULE'):
        env.pop(k, None)
    env['DJANGO_SETTINGS_MODULE'] = 'config.settings'
    return env


def part_path(label):
    return SYNC_DIR / (label.replace('.', '_') + '.json')


def dump_label(label, env, retries=3):
    out = part_path(label)
    for attempt in range(1, retries + 1):
        print('Dump', label, f'(intento {attempt})')
        proc = subprocess.run(
            [
                sys.executable, 'manage.py', 'dumpdata', label,
                '--natural-foreign', '--natural-primary', '--indent', '2',
                '-o', str(out),
            ],
            env=env,
        )
        if proc.returncode == 0 and out.is_file() and out.stat().st_size > 2:
            print('  OK {:.1f} KB'.format(out.stat().st_size / 1024))
            return
        print('  fallo, reintento...')
        time.sleep(3)
    raise RuntimeError('No se pudo exportar ' + label)


def ensure_firewall(token):
    ip = urllib.request.urlopen('https://api.ipify.org', timeout=10).read().decode().strip()
    api(token, 'PUT', f'/databases/{DB_ID}/firewall', {
        'rules': [{'type': 'app', 'value': APP_ID}, {'type': 'ip_addr', 'value': ip}],
    })
    print('Firewall OK:', ip)
    time.sleep(3)


def restore_firewall(token):
    api(token, 'PUT', f'/databases/{DB_ID}/firewall', {
        'rules': [{'type': 'app', 'value': APP_ID}],
    })
    print('Firewall restaurado')


def dump_all(token):
    ensure_firewall(token)
    env = {**os.environ, **prod_env()}
    SYNC_DIR.mkdir(parents=True, exist_ok=True)
    try:
        for label in CORE_PARTS:
            dump_label(label, env)
        for label in POS_MODELS:
            dump_label(label, env)
    finally:
        restore_firewall(token)


def import_all():
    env = local_env()
    print('Flush SQLite local...')
    subprocess.run([sys.executable, 'manage.py', 'flush', '--no-input'], env=env, check=True)
    for label in LOAD_ORDER:
        path = part_path(label)
        if not path.is_file():
            raise RuntimeError('Falta parte: ' + str(path))
        print('Load', path.name)
        subprocess.run([sys.executable, 'manage.py', 'loaddata', str(path)], env=env, check=True)


def bootstrap():
    env = local_env()
    for args in (
        ['sync_company_constancia'],
        ['ensure_dni_api_module'],
        ['ensure_whatsapp_module'],
        ['ensure_advisory_progress_module', '--group-id=1'],
        ['ensure_collector_module', '--group-id=1'],
        ['ensure_contracts_report_module'],
        ['repair_module_layout'],
        ['ensure_admin_group_access'],
        ['ensure_neo_superuser', f'--password={read_spec_value("NEO_ADMIN_PASSWORD")}'],
    ):
        subprocess.run([sys.executable, 'manage.py', *args], env=env, check=True)


def counts():
    env = local_env()
    subprocess.run([
        sys.executable, '-c',
        'import django; django.setup(); '
        'from core.user.models import User; from core.pos.models import Client, Sale; '
        'print("Usuarios", User.objects.count(), "| Clientes", Client.objects.count(), "| Ventas", Sale.objects.count())',
    ], env=env, check=True)


def main():
    import sys as _sys
    token = load_token()
    if len(_sys.argv) > 1 and _sys.argv[1] == 'import-only':
        import_all()
        bootstrap()
        counts()
        print('LISTO (import-only)')
        return
    dump_all(token)
    import_all()
    bootstrap()
    counts()
    print('LISTO')


if __name__ == '__main__':
    main()
