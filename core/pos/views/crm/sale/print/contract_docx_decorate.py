"""
Decoración plantilla contrato Celia: N° correlativo (CT-######), barcode y QR (cliente + venta).
"""
from __future__ import annotations

import logging
import os
import re
import struct
from io import BytesIO

logger = logging.getLogger(__name__)

from core.pos.views.crm.sale.print.docx_codes import (
    _generate_barcode_png,
    _generate_qr_png,
    decoration_deps_available,
    resize_png_stream,
)

SERIAL_SAMPLE = '000000004'
SERIAL_PLACEHOLDER = '000000001'

# image4 = sello/firma + logo (no tocar). image5 / pie image3 = barcode. image6 = QR.
CONTRACT_SEAL_IMAGE = 'image4.png'
CONTRACT_BARCODE_IMAGES = frozenset({'image5.png', 'image3.png'})
CONTRACT_QR_IMAGE = 'image6.png'


def contract_serial_display(contract_code):
    """CT-000004 → 000000004 (nueve dígitos según número de contrato)."""
    cc = (contract_code or '').strip()
    m = re.search(r'(\d+)\s*$', cc)
    n = int(m.group(1)) if m else 0
    return '{:09d}'.format(n)


def contract_codes_payload(client_code, sale_code):
    parts = [
        (client_code or '').strip(),
        (sale_code or '').strip(),
    ]
    parts = [p for p in parts if p]
    if not parts:
        return 'VT-000000'
    return '-'.join(parts)


def _replace_serial_in_xml_parts(docx_bytes, serial_fmt):
    from zipfile import ZipFile, ZIP_DEFLATED

    zin_mem = BytesIO(docx_bytes)
    zout_mem = BytesIO()
    with ZipFile(zin_mem, 'r') as zin, ZipFile(zout_mem, 'w', ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            content = zin.read(item.filename)
            if item.filename.startswith('word/') and item.filename.endswith('.xml'):
                txt = content.decode('utf-8', 'ignore')
                if SERIAL_SAMPLE in txt:
                    txt = txt.replace(SERIAL_SAMPLE, serial_fmt)
                if SERIAL_PLACEHOLDER in txt:
                    txt = txt.replace(SERIAL_PLACEHOLDER, serial_fmt)
                txt = re.sub(
                    r'(N[°º]\s*</w:t></w:r>.*?<w:t[^>]*>)\s*0{6,9}\s*(</w:t>)',
                    r'\g<1>' + serial_fmt + r'\g<2>',
                    txt,
                    flags=re.DOTALL,
                )
                content = txt.encode('utf-8')
            zout.writestr(item, content)
    return zout_mem.getvalue()


def _rels_may_decorate_images(rels_name):
    if not rels_name.startswith('word/_rels/') or not rels_name.endswith('.rels'):
        return False
    if 'header' in rels_name.lower():
        return False
    if rels_name == 'word/_rels/document.xml.rels':
        return True
    return 'footer' in rels_name.lower()


def _image_kind_from_name(filename):
    base = os.path.basename(filename).lower()
    if base == CONTRACT_SEAL_IMAGE:
        return None
    if base in CONTRACT_BARCODE_IMAGES:
        return 'barcode'
    if base == CONTRACT_QR_IMAGE:
        return 'qr'
    return None


def _replace_barcode_qr_images(docx_bytes, payload):
    if not payload or not decoration_deps_available():
        return docx_bytes

    from zipfile import ZipFile, ZIP_DEFLATED
    import xml.etree.ElementTree as ET

    bc_png = _generate_barcode_png(payload)
    qr_png = _generate_qr_png(payload)
    if bc_png is None and qr_png is None:
        return docx_bytes

    zin_mem = BytesIO(docx_bytes)
    zout_mem = BytesIO()

    try:
        with ZipFile(zin_mem, 'r') as zin:
            replacements = {}
            for rels_name in zin.namelist():
                if not _rels_may_decorate_images(rels_name):
                    continue
                rels_root = ET.fromstring(zin.read(rels_name).decode('utf-8', 'ignore'))
                for rel in rels_root:
                    target = rel.get('Target', '')
                    if 'image' not in rel.get('Type', '').lower() or not target:
                        continue
                    full_path = 'word/' + target.lstrip('/')
                    if full_path not in zin.namelist():
                        continue
                    kind = _image_kind_from_name(full_path)
                    if not kind:
                        continue
                    data = zin.read(full_path)
                    if len(data) < 24 or data[:4] != b'\x89PNG':
                        continue
                    w = struct.unpack('>I', data[16:20])[0]
                    h = struct.unpack('>I', data[20:24])[0]
                    replacements[full_path] = (kind, w, h)

            if not replacements:
                return docx_bytes

            with ZipFile(zout_mem, 'w', ZIP_DEFLATED) as zout:
                for item in zin.infolist():
                    content = zin.read(item.filename)
                    spec = replacements.get(item.filename)
                    if spec:
                        kind, tw, th = spec
                        if kind == 'barcode' and bc_png is not None:
                            content = resize_png_stream(bc_png, tw, th)
                        elif kind == 'qr' and qr_png is not None:
                            content = resize_png_stream(qr_png, tw, th)
                    zout.writestr(item, content)
            return zout_mem.getvalue()
    except Exception as exc:
        logger.warning('Contrato Celia: no se reemplazaron imágenes barcode/QR: %s', exc)
        return docx_bytes


def decorate_contract_celia_docx(docx_bytes, client_code, sale_code, contract_code):
    serial_fmt = contract_serial_display(contract_code)
    payload = contract_codes_payload(client_code, sale_code)
    docx_bytes = _replace_serial_in_xml_parts(docx_bytes, serial_fmt)
    docx_bytes = _replace_barcode_qr_images(docx_bytes, payload)
    return docx_bytes
