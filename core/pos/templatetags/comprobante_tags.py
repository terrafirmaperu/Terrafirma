from django import template

from core.pos.brand_assets import COMPROBANTE_RUC, comprobante_logo_file_uri

register = template.Library()


@register.simple_tag
def comprobante_ruc():
    return COMPROBANTE_RUC


@register.simple_tag(takes_context=True)
def comprobante_logo(context):
    """Usa la URL del contexto (HTTP en HTML / file:// en PDF); evita file:// en el navegador."""
    value = context.get('comprobante_logo')
    if value:
        return value
    return comprobante_logo_file_uri()
