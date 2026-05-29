"""
Configuración de producción (DigitalOcean Droplet o App Platform).

  export DJANGO_SETTINGS_MODULE=config.production

Variables obligatorias: DJANGO_SECRET_KEY
Recomendadas: DJANGO_ALLOWED_HOSTS, DATABASE_URL (PostgreSQL en DO)
"""

import os

from config.settings import *  # noqa: F403, F401

DEBUG = False

SECRET_KEY = os.environ['DJANGO_SECRET_KEY']

_allowed = os.environ.get('DJANGO_ALLOWED_HOSTS', '').strip()
if not _allowed:
    raise ValueError('Defina DJANGO_ALLOWED_HOSTS (ej. terrafirmaperu.com,www.terrafirmaperu.com)')
ALLOWED_HOSTS = [h.strip() for h in _allowed.split(',') if h.strip()]

DATABASES = __import__('config.db', fromlist=['get_databases']).get_databases()

# HTTPS detrás de nginx / balanceador DigitalOcean
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = os.environ.get('DJANGO_SECURE_SSL_REDIRECT', '1') == '1'
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

_hsts = os.environ.get('DJANGO_HSTS', '1') == '1'
if _hsts:
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

CSRF_TRUSTED_ORIGINS = []
for host in ALLOWED_HOSTS:
    if host and host != '*':
        CSRF_TRUSTED_ORIGINS.append('https://{}'.format(host))

SESSION_SERIALIZER = 'django.contrib.sessions.serializers.JSONSerializer'

# Archivos estáticos vía WhiteNoise (media sigue en disco + nginx)
MIDDLEWARE = list(MIDDLEWARE)  # noqa: F405
if 'whitenoise.middleware.WhiteNoiseMiddleware' not in MIDDLEWARE:
    sec_idx = MIDDLEWARE.index('django.middleware.security.SecurityMiddleware')
    MIDDLEWARE.insert(sec_idx + 1, 'whitenoise.middleware.WhiteNoiseMiddleware')

STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'

LOCALHOST = os.environ.get('DJANGO_PUBLIC_HOST', ALLOWED_HOSTS[0])

EMAIL_HOST = os.environ.get('EMAIL_HOST', EMAIL_HOST)  # noqa: F405
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', str(EMAIL_PORT)))  # noqa: F405
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', EMAIL_HOST_USER)  # noqa: F405
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', EMAIL_HOST_USER or DEFAULT_FROM_EMAIL)  # noqa: F405

DNI_API_TOKEN = os.environ.get('DNI_API_TOKEN', '')
if not DNI_API_TOKEN:
    import warnings
    warnings.warn('DNI_API_TOKEN no definido: consulta RENIEC deshabilitada.', stacklevel=1)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'WARNING',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'django.log'),  # noqa: F405
            'formatter': 'verbose',
        },
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}
