from django import template

from core.pos.brand_assets import COMPROBANTE_RUC, comprobante_logo_file_uri

register = template.Library()


@register.simple_tag
def comprobante_ruc():
    return COMPROBANTE_RUC


@register.simple_tag
def comprobante_logo():
    return comprobante_logo_file_uri()
