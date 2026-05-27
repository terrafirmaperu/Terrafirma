from django.conf import settings

from core.marketing.client_portal import get_portal_client
from core.marketing.site_content import get_site_info


def marketing_site(request):
    info = get_site_info()
    return {
        'SITE_NAME': getattr(settings, 'SITE_NAME', None) or info.get('site_name') or 'Terrafirma',
        'site_info': info,
    }


def marketing_client_portal(request):
    return {
        'cliente_portal': get_portal_client(request),
    }
