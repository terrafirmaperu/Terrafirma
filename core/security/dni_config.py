"""Lectura de configuración DNI: base de datos con respaldo en variables de entorno."""

from config import settings


def get_dni_api_settings():
    """
    Devuelve dict con url_template, token, timeout, enabled, source.
    Prioridad: registro en Seguridad → variables DNI_API_* en entorno.
    """
    from core.security.models import DniApiConfiguration

    cfg = DniApiConfiguration.objects.order_by('id').first()
    env_url = (
        getattr(settings, 'DNI_API_URL', None)
        or DniApiConfiguration.DEFAULT_API_URL
    )
    env_token = (getattr(settings, 'DNI_API_TOKEN', '') or '').strip()
    env_timeout = int(getattr(settings, 'DNI_API_TIMEOUT', 12) or 12)

    if cfg is not None:
        url = (cfg.api_url or '').strip() or env_url
        token = (cfg.api_token or '').strip() or env_token
        timeout = cfg.api_timeout or env_timeout
        return {
            'url_template': url,
            'token': token,
            'timeout': timeout,
            'enabled': bool(cfg.is_enabled),
            'provider_name': (cfg.provider_name or '').strip() or 'API DNI',
            'source': 'database' if cfg.token_configured() or (cfg.api_url or '').strip() else 'database+env',
        }

    return {
        'url_template': env_url,
        'token': env_token,
        'timeout': env_timeout,
        'enabled': True,
        'provider_name': 'Variables de entorno',
        'source': 'env',
    }
