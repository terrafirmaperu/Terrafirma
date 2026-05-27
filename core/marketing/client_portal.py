"""Portal web del cliente (sesión propia, independiente del login Factora)."""

MARKETING_CLIENT_PORTAL_SESSION_KEY = 'marketing_client_portal_id'


def get_portal_client(request):
    """Cliente (`core.pos.models.Client`) si la sesión del portal es válida; si no, None."""
    pk = request.session.get(MARKETING_CLIENT_PORTAL_SESSION_KEY)
    if not pk:
        return None
    from core.pos.models import Client

    try:
        return Client.objects.select_related('user').get(pk=pk)
    except Client.DoesNotExist:
        request.session.pop(MARKETING_CLIENT_PORTAL_SESSION_KEY, None)
        return None
