"""
Barcode (abajo izquierda) y N° correlativo (abajo derecha) en la plantilla Word.
Solo se reemplaza en el cuerpo del documento (cuadros de texto anclados), sin mover el diseño.
"""
from __future__ import annotations

import logging
import re
import struct
from io import BytesIO

logger = logging.getLogger(__name__)

try:
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Inches, Pt, RGBColor
except ImportError:
    Document = None  # type: ignore

from core.pos.views.crm.sale.print.docx_codes import (
    _generate_barcode_png,
    decoration_deps_available,
    resize_png_stream,
)

CONSTANCIA_BARCODE_IMAGE = 'image3.png'

MARK_BARCODE = '[[POLARISS_CONSTANCIA_BARCODE]]'
MARK_NUMBER = '[[POLARISS_CONSTANCIA_NRO]]'
SERIAL_PLACEHOLDER = '000000001'


def barcode_payload(client_code, contract_code, sale_code):
    """Código de barras: cliente + contrato + venta (antifalsificación)."""
    parts = [
        (client_code or '').strip(),
        (contract_code or '').strip(),
        (sale_code or '').strip(),
    ]
    parts = [p for p in parts if p]
    if not parts:
        return 'VT-000000'
    return '-'.join(parts)


def _replace_barcode_image_document(docx_bytes, barcode_png):
    if not barcode_png:
        return docx_bytes
    from zipfile import ZipFile, ZIP_DEFLATED

    zin_mem = BytesIO(docx_bytes)
    zout_mem = BytesIO()
    try:
        with ZipFile(zin_mem, 'r') as zin:
            rels_path = 'word/_rels/document.xml.rels'
            if rels_path not in zin.namelist():
                return docx_bytes
            import xml.etree.ElementTree as ET

            rels_root = ET.fromstring(zin.read(rels_path).decode('utf-8', 'ignore'))
            barcode_path = None
            tpl_w = tpl_h = 0
            for rel in rels_root:
                target = rel.get('Target', '')
                if 'image' not in rel.get('Type', '').lower() or not target:
                    continue
                if not target.replace('\\', '/').endswith(CONSTANCIA_BARCODE_IMAGE):
                    continue
                full_path = 'word/' + target.lstrip('/')
                if full_path not in zin.namelist():
                    continue
                data = zin.read(full_path)
                if len(data) < 24 or data[:4] != b'\x89PNG':
                    continue
                barcode_path = full_path
                tpl_w = struct.unpack('>I', data[16:20])[0]
                tpl_h = struct.unpack('>I', data[20:24])[0]
                break

            if not barcode_path:
                return docx_bytes

            bc_bytes = resize_png_stream(barcode_png, tpl_w, tpl_h)
            with ZipFile(zout_mem, 'w', ZIP_DEFLATED) as zout:
                for item in zin.infolist():
                    content = zin.read(item.filename)
                    if item.filename == barcode_path:
                        content = bc_bytes
                    zout.writestr(item, content)
            return zout_mem.getvalue()
    except Exception as exc:
        logger.warning('Constancia: no se reemplazó imagen de barcode: %s', exc)
        return docx_bytes


def _replace_serial_in_document_xml(docx_bytes, serial_number):
    serial_fmt = '{:09d}'.format(int(serial_number or 0))
    zin_mem = BytesIO(docx_bytes)
    zout_mem = BytesIO()
    from zipfile import ZipFile, ZIP_DEFLATED

    with ZipFile(zin_mem, 'r') as zin, ZipFile(zout_mem, 'w', ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            content = zin.read(item.filename)
            if item.filename == 'word/document.xml':
                txt = content.decode('utf-8', 'ignore')
                if SERIAL_PLACEHOLDER in txt:
                    txt = txt.replace(SERIAL_PLACEHOLDER, serial_fmt)
                if MARK_NUMBER in txt:
                    txt = txt.replace(MARK_NUMBER, serial_fmt)
                txt = re.sub(
                    r'(N[°º]\s*</w:t></w:r>.*?<w:t[^>]*>)\s*0{6,9}\s*(</w:t>)',
                    r'\g<1>' + serial_fmt + r'\g<2>',
                    txt,
                    flags=re.DOTALL,
                )
                content = txt.encode('utf-8')
            zout.writestr(item, content)
    return zout_mem.getvalue()


def decorate_constancia_docx(docx_bytes, client_code, contract_code, sale_code, serial_number):
    payload = barcode_payload(client_code, contract_code, sale_code)
    serial = int(serial_number or 0)
    bc_png = _generate_barcode_png(payload) if decoration_deps_available() else None

    docx_bytes = _replace_serial_in_document_xml(docx_bytes, serial)
    docx_bytes = _replace_barcode_image_document(docx_bytes, bc_png)
    return docx_bytes


def strip_header_markers_from_parts(header_footer_parts):
    """Quita marcadores POLARISS del encabezado si quedaron arriba por error."""
    out = {}
    for name, raw in header_footer_parts.items():
        if not name.endswith('.xml'):
            out[name] = raw
            continue
        txt = raw.decode('utf-8', 'ignore')
        if MARK_BARCODE not in txt and MARK_NUMBER not in txt:
            out[name] = raw
            continue
        txt = re.sub(
            r'<w:p[^>]*>.*?POLARISS_CONSTANCIA_(?:BARCODE|NRO).*?</w:p>',
            '',
            txt,
            flags=re.DOTALL,
        )
        out[name] = txt.encode('utf-8')
    return out
