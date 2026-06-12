"""Rutas de marca Terrafirma para comprobantes (ticket/factura PDF).

No usar en contratos Word: esos llevan su propio diseño en la plantilla .docx.
"""
import os
from pathlib import Path

from django.conf import settings

# Ruta relativa dentro de static/ — versionada en Git y servida con collectstatic en deploy.
COMPROBANTE_LOGO_STATIC = 'img/terrafirma_comprobante_logo.png'
COMPROBANTE_RUC = '20612888141'


def _resolve_comprobante_logo_path():
    """Devuelve la ruta absoluta del PNG (staticfiles/ en producción, static/ en dev)."""
    candidates = (
        os.path.join(settings.STATIC_ROOT, COMPROBANTE_LOGO_STATIC),
        os.path.join(settings.BASE_DIR, 'static', COMPROBANTE_LOGO_STATIC),
    )
    for path in candidates:
        if os.path.isfile(path):
            return path
    return candidates[-1]


def comprobante_logo_url():
    """URL pública del logo (navegador / vistas HTML)."""
    return '{}{}'.format(settings.STATIC_URL, COMPROBANTE_LOGO_STATIC)


def comprobante_logo_file_uri():
    """URI file:// para WeasyPrint al generar PDF de comprobantes."""
    return Path(_resolve_comprobante_logo_path()).as_uri()


def comprobante_print_context():
    """Datos fijos de marca para plantillas PDF de comprobantes."""
    return {
        'comprobante_logo': comprobante_logo_file_uri(),
        'comprobante_ruc': COMPROBANTE_RUC,
    }
