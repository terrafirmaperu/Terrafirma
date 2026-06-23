#!/usr/bin/env python
"""Importa db/prod_parts/*.json en SQLite local (orden FK correcto)."""
import os
import re
import subprocess
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_DIR))
os.chdir(APP_DIR)
SYNC_DIR = APP_DIR / 'db' / 'prod_parts'

LOAD_ORDER = [
    'auth.group', 'user', 'security', 'whatsapp',
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


def local_env():
    env = os.environ.copy()
    for k in ('DATABASE_URL', 'DJANGO_SECRET_KEY', 'DJANGO_SETTINGS_MODULE'):
        env.pop(k, None)
    env['DJANGO_SETTINGS_MODULE'] = 'config.settings'
    return env


def read_spec_value(key):
    text = (APP_DIR / '.do' / 'app-spec.local.yaml').read_text(encoding='utf-8')
    block = re.search(rf'- key:\s*{re.escape(key)}\s*\n((?:\s+.+\n)+)', text)
    for line in block.group(1).splitlines():
        if line.strip().startswith('value:'):
            raw = line.strip().split(':', 1)[1].strip()
            return raw[1:-1] if raw.startswith('"') and raw.endswith('"') else raw
    raise RuntimeError(key)


def path_for(label):
    return SYNC_DIR / (label.replace('.', '_') + '.json')


def main():
    env = local_env()
    print('Flush...')
    subprocess.run([sys.executable, 'manage.py', 'flush', '--no-input'], env=env, check=True)
    for label in LOAD_ORDER:
        p = path_for(label)
        if not p.is_file():
            raise SystemExit('Falta: ' + str(p))
        print('Load', p.name)
        subprocess.run([sys.executable, 'manage.py', 'loaddata', str(p)], env=env, check=True)
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
    subprocess.run([
        sys.executable, '-c',
        'import django; django.setup(); '
        'from core.user.models import User; from core.pos.models import Client, Sale, CtasCollect; '
        'print("Usuarios", User.objects.count()); '
        'print("Clientes", Client.objects.count()); '
        'print("Ventas", Sale.objects.count()); '
        'print("Cobranzas", CtasCollect.objects.count())',
    ], env=env, check=True)
    print('LISTO')


if __name__ == '__main__':
    main()
