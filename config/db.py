import os
from urllib.parse import parse_qs, unquote, urlparse

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SQLITE = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.environ.get(
            'SQLITE_PATH',
            os.path.join(BASE_DIR, 'db', 'polariss.sqlite3'),
        ),
    }
}

POSTGRESQL = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('POSTGRES_DB', 'terrafirma'),
        'USER': os.environ.get('POSTGRES_USER', 'terrafirma'),
        'PASSWORD': os.environ.get('POSTGRES_PASSWORD', ''),
        'HOST': os.environ.get('POSTGRES_HOST', 'localhost'),
        'PORT': os.environ.get('POSTGRES_PORT', '5432'),
        'ATOMIC_REQUESTS': True,
        'CONN_MAX_AGE': int(os.environ.get('POSTGRES_CONN_MAX_AGE', '60')),
        'OPTIONS': {},
    }
}

if os.environ.get('POSTGRES_SSLMODE'):
    POSTGRESQL['default']['OPTIONS']['sslmode'] = os.environ['POSTGRES_SSLMODE']


def _database_from_url(url):
    parsed = urlparse(url)
    engine = parsed.scheme
    if engine in ('postgres', 'postgresql'):
        django_engine = 'django.db.backends.postgresql'
    elif engine == 'mysql':
        django_engine = 'django.db.backends.mysql'
    else:
        raise ValueError('Esquema DATABASE_URL no soportado: {}'.format(engine))
    name = (parsed.path or '').lstrip('/')
    options = {}
    query = parse_qs(parsed.query)
    if 'sslmode' in query:
        options['sslmode'] = query['sslmode'][0]
    elif os.environ.get('POSTGRES_SSLMODE'):
        options['sslmode'] = os.environ['POSTGRES_SSLMODE']
    cfg = {
        'ENGINE': django_engine,
        'NAME': unquote(name),
        'USER': unquote(parsed.username or ''),
        'PASSWORD': unquote(parsed.password or ''),
        'HOST': parsed.hostname or '',
        'PORT': str(parsed.port or ''),
        'ATOMIC_REQUESTS': True,
        'CONN_MAX_AGE': int(os.environ.get('POSTGRES_CONN_MAX_AGE', '60')),
    }
    if options:
        cfg['OPTIONS'] = options
    return {'default': cfg}


def get_databases():
    """
    Producción: DATABASE_URL (App Platform / Managed DB) o variables POSTGRES_*.
    Desarrollo: SQLite por defecto en settings.py.
    """
    url = os.environ.get('DATABASE_URL', '').strip()
    if url:
        return _database_from_url(url)
    if os.environ.get('DJANGO_DB_ENGINE', '').lower() in ('postgres', 'postgresql'):
        return POSTGRESQL
    return SQLITE


# Compatibilidad con imports existentes
MYSQL = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'db',
        'USER': 'root',
        'PASSWORD': '123',
        'HOST': 'localhost',
        'PORT': '',
    }
}

SQLSERVER = {
    'default': {
        'ENGINE': 'sql_server.pyodbc',
        'NAME': 'db',
        'USER': '',
        'PASSWORD': '',
        'HOST': 'localhost',
        'PORT': '1433',
        'OPTIONS': {
            'driver': 'SQL Server Native Client 10.0',
        },
    },
}
