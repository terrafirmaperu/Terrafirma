#!/usr/bin/env python
"""Sincroniza produccion DO -> SQLite local (.env.deploy + .do/app-spec.local.yaml)."""
import json
import os
import re
import shutil
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

SECURITY_PARTS = [
    'security.dashboard',
    'security.moduletype',
    'security.module',
    'security.groupmodule',
    'security.grouppermission',
    'security.databasebackups',
    'security.accessusers',
    'security.dniapiconfiguration',
    'security.supervisorauditlog',
]

# No bloquean el panel local si fallan al exportar de producción
SECURITY_OPTIONAL = frozenset({
    'security.databasebackups',
    'security.supervisorauditlog',
})

CORE_PARTS = ['auth.group', 'user'] + SECURITY_PARTS + ['whatsapp']
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


def part_path(label):
    if label == 'security':
        return SYNC_DIR / 'security.json'
    return SYNC_DIR / (label.replace('.', '_') + '.json')


def security_load_labels():
    if part_path('security.dashboard').is_file():
        return list(SECURITY_PARTS)
    legacy = SYNC_DIR / 'security.json'
    if legacy.is_file() and legacy.stat().st_size > 3:
        return ['security']
    return []


def import_load_order():
    labels = ['auth.group', 'user']
    sec = security_load_labels()
    if not sec:
        raise RuntimeError(
            'Falta security.json o archivos security_*.json en db/prod_parts'
        )
    labels.extend(sec)
    labels.append('whatsapp')
    labels.extend(POS_MODELS)
    return labels


def load_token():
    env_path = APP_DIR / '.env.deploy'
    if not env_path.is_file():
        raise RuntimeError('Falta .env.deploy con DIGITALOCEAN_ACCESS_TOKEN')
    for line in env_path.read_text(encoding='utf-8').splitlines():
        if line.startswith('DIGITALOCEAN_ACCESS_TOKEN='):
            return line.split('=', 1)[1].strip()
    raise RuntimeError('Falta DIGITALOCEAN_ACCESS_TOKEN en .env.deploy')


def _load_deploy_env():
    data = {}
    env_path = APP_DIR / '.env.deploy'
    if not env_path.is_file():
        return data
    for raw_line in env_path.read_text(encoding='utf-8').splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, _, value = line.partition('=')
        data[key.strip()] = value.strip().strip('"').strip("'")
    return data


def read_spec_value(key):
    deploy = _load_deploy_env()
    if deploy.get(key):
        return deploy[key]

    spec_path = APP_DIR / '.do' / 'app-spec.local.yaml'
    if not spec_path.is_file():
        raise RuntimeError(
            'Falta {} en .env.deploy o .do/app-spec.local.yaml'.format(key)
        )
    text = spec_path.read_text(encoding='utf-8')
    block = re.search(rf'- key:\s*{re.escape(key)}\s*\n((?:\s+.+\n)+)', text)
    if not block:
        raise RuntimeError(key)
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


def validate_fixture(path):
    json.loads(Path(path).read_text(encoding='utf-8'))


def ensure_optional_fixture(label):
    path = part_path(label)
    if path.is_file() and path.stat().st_size >= 2:
        try:
            validate_fixture(path)
            return
        except json.JSONDecodeError:
            pass
    path.write_text('[]\n', encoding='utf-8')


def validate_all_parts():
    missing = []
    invalid = []
    for label in import_load_order():
        path = part_path(label)
        if label in SECURITY_OPTIONAL:
            ensure_optional_fixture(label)
            continue
        if not path.is_file() or path.stat().st_size < 2:
            missing.append(path.name)
            continue
        try:
            validate_fixture(path)
        except json.JSONDecodeError as exc:
            invalid.append('{} ({})'.format(path.name, exc))
    if missing:
        raise RuntimeError('Faltan respaldos: ' + ', '.join(missing))
    if invalid:
        raise RuntimeError('JSON invalido: ' + '; '.join(invalid))


def dump_label(label, env, retries=3):
    out = part_path(label)
    optional = label in SECURITY_OPTIONAL
    for attempt in range(1, retries + 1):
        print('Dump', label, f'(intento {attempt})')
        proc = subprocess.run(
            [
                sys.executable, 'manage.py', 'dumpdata', label,
                '--natural-foreign', '--natural-primary', '--indent', '2',
                '-o', str(out),
            ],
            env=env,
            capture_output=True,
            text=True,
        )
        if proc.returncode == 0 and out.is_file() and out.stat().st_size > 1:
            try:
                validate_fixture(out)
                print('  OK {:.1f} KB'.format(out.stat().st_size / 1024))
                return
            except json.JSONDecodeError as exc:
                print('  JSON invalido:', exc)
        else:
            err = (proc.stderr or proc.stdout or '').strip()
            if err:
                print('  ', err.splitlines()[-1][:200])
        print('  fallo, reintento...')
        time.sleep(5)
    if optional:
        out.write_text('[]\n', encoding='utf-8')
        print('  opcional omitido -> []')
        return
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
        for label in CORE_PARTS + POS_MODELS:
            dump_label(label, env)
    finally:
        restore_firewall(token)


def backup_local_db():
    db = APP_DIR / 'db' / 'polariss.sqlite3'
    if not db.is_file():
        return
    bak = APP_DIR / 'db' / ('polariss.sqlite3.bak-' + time.strftime('%Y%m%d-%H%M%S'))
    shutil.copy2(db, bak)
    print('Respaldo SQLite:', bak.name)


def import_all():
    print('Validando respaldos en db/prod_parts...')
    validate_all_parts()
    env = local_env()
    backup_local_db()
    print('Flush SQLite local...')
    subprocess.run([sys.executable, 'manage.py', 'flush', '--no-input'], env=env, check=True)
    for label in import_load_order():
        path = part_path(label)
        print('Load', path.name)
        subprocess.run([sys.executable, 'manage.py', 'loaddata', str(path)], env=env, check=True)


def bootstrap():
    env = local_env()
    neo_pwd = 'lafamilia123456789'
    try:
        neo_pwd = read_spec_value('NEO_ADMIN_PASSWORD')
    except RuntimeError:
        pass
    steps = (
        ['sync_company_constancia'],
        ['ensure_dni_api_module'],
        ['ensure_whatsapp_module'],
        ['ensure_advisory_progress_module', '--group-id=1'],
        ['ensure_collector_module', '--group-id=1'],
        ['ensure_contracts_report_module'],
        ['repair_module_layout'],
        ['ensure_role_groups'],
        ['ensure_neo_superuser', f'--password={neo_pwd}'],
        ['assign_supervisor_group', '--username=Neo'],
        ['repair_panel'],
    )
    for args in steps:
        subprocess.run([sys.executable, 'manage.py', *args], env=env, check=True)


def counts():
    env = local_env()
    subprocess.run([
        sys.executable, '-c',
        'import django; django.setup(); '
        'from core.user.models import User; '
        'from core.pos.models import Client, Sale, CtasCollect, PaymentsCtaCollect; '
        'print('
        '"Usuarios", User.objects.count(), '
        '"| Clientes", Client.objects.count(), '
        '"| Ventas", Sale.objects.count(), '
        '"| Cobranzas", CtasCollect.objects.count(), '
        '"| Pagos CxC", PaymentsCtaCollect.objects.count())',
    ], env=env, check=True)


def main():
    if len(sys.argv) > 1 and sys.argv[1] == 'validate-only':
        validate_all_parts()
        print('Respaldos OK en db/prod_parts')
        return
    if len(sys.argv) > 1 and sys.argv[1] in ('dump-only', 'download-only'):
        token = load_token()
        dump_all(token)
        validate_all_parts()
        print('LISTO (descarga a db/prod_parts)')
        return
    if len(sys.argv) > 1 and sys.argv[1] == 'import-only':
        import_all()
        bootstrap()
        counts()
        print('LISTO (import-only)')
        return
    token = load_token()
    dump_all(token)
    import_all()
    bootstrap()
    counts()
    print('LISTO')


if __name__ == '__main__':
    main()
