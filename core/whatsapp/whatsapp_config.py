import os

from core.whatsapp.models import WhatsAppApiConfiguration


def get_whatsapp_api_settings():
    """Devuelve dict listo para whatsapp_api o None si no está configurado."""
    cfg = WhatsAppApiConfiguration.get_solo()
    if cfg.pk is None:
        env_token = (os.environ.get('WHATSAPP_API_TOKEN') or '').strip()
        env_phone = (os.environ.get('WHATSAPP_PHONE_NUMBER_ID') or '').strip()
        if env_token or env_phone:
            return {
                'enabled': True,
                'provider_name': cfg.provider_name,
                'phone_number_id': env_phone or cfg.phone_number_id,
                'phone_number_display': cfg.phone_number_display,
                'business_account_id': cfg.business_account_id,
                'api_base_url': cfg.api_base_url,
                'api_version': cfg.api_version,
                'api_token': env_token or cfg.api_token,
                'api_timeout': cfg.api_timeout,
                'messages_endpoint': cfg.get_messages_endpoint(),
            }
        return None

    if not cfg.is_enabled or not cfg.token_configured() or not (cfg.phone_number_id or '').strip():
        env_token = (os.environ.get('WHATSAPP_API_TOKEN') or '').strip()
        env_phone = (os.environ.get('WHATSAPP_PHONE_NUMBER_ID') or '').strip()
        if env_token and env_phone:
            base = (cfg.api_base_url or WhatsAppApiConfiguration.DEFAULT_API_BASE).rstrip('/')
            version = (cfg.api_version or WhatsAppApiConfiguration.DEFAULT_API_VERSION).strip('/')
            return {
                'enabled': True,
                'provider_name': cfg.provider_name,
                'phone_number_id': env_phone,
                'phone_number_display': cfg.phone_number_display,
                'business_account_id': cfg.business_account_id,
                'api_base_url': cfg.api_base_url,
                'api_version': cfg.api_version,
                'api_token': env_token,
                'api_timeout': cfg.api_timeout,
                'messages_endpoint': '{}/{}/{}/messages'.format(base, version, env_phone),
            }
        return None

    return {
        'enabled': cfg.is_enabled,
        'provider_name': cfg.provider_name,
        'phone_number_id': cfg.phone_number_id,
        'phone_number_display': cfg.phone_number_display,
        'business_account_id': cfg.business_account_id,
        'api_base_url': cfg.api_base_url,
        'api_version': cfg.api_version,
        'api_token': cfg.api_token,
        'api_timeout': cfg.api_timeout,
        'messages_endpoint': cfg.get_messages_endpoint(),
    }
