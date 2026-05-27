"""Fusiona cuerpo rellenado con encabezados/pies originales de la plantilla."""
from __future__ import annotations

from io import BytesIO
from zipfile import ZipFile, ZIP_DEFLATED

from core.pos.views.frm.ctascollect.constancia_docx_decorate import strip_header_markers_from_parts


def _header_footer_names(zip_names):
    for name in zip_names:
        if (
            name.startswith('word/header')
            or name.startswith('word/footer')
            or name.startswith('word/_rels/header')
            or name.startswith('word/_rels/footer')
        ):
            yield name


def prepare_header_footer_parts(template_bytes):
    """Copia encabezados/pies de la plantilla sin alterar barcode ni N° (están en el cuerpo)."""
    parts = {}
    with ZipFile(BytesIO(template_bytes), 'r') as zin:
        for name in _header_footer_names(zin.namelist()):
            parts[name] = zin.read(name)
    return strip_header_markers_from_parts(parts)


def merge_docx_with_template_headers(body_docx_bytes, template_bytes, header_footer_parts):
    zout = BytesIO()
    with ZipFile(BytesIO(body_docx_bytes), 'r') as zb, ZipFile(zout, 'w', ZIP_DEFLATED) as zo:
        body_names = set()
        for item in zb.infolist():
            body_names.add(item.filename)
            zo.writestr(item, header_footer_parts.get(item.filename, zb.read(item.filename)))
        for name, content in header_footer_parts.items():
            if name not in body_names:
                zo.writestr(name, content)
    return zout.getvalue()
