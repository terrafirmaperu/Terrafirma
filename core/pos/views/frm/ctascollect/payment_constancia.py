import logging
import os
import re
from decimal import Decimal
from io import BytesIO
from config import settings
from core.pos.models import Company
from core.pos.views.frm.ctascollect.constancia_docx_decorate import decorate_constancia_docx
from core.pos.views.frm.ctascollect.constancia_docx_merge import (
    merge_docx_with_template_headers,
    prepare_header_footer_parts,
)
from core.pos.views.frm.ctascollect.constancia_xml_fill import fill_constancia_doc_paragraphs
from core.pos.views.crm.sale.print.views import MONTHS_ES_UPPER

logger = logging.getLogger(__name__)

try:
    from docx import Document
except ImportError:
    Document = None  # type: ignore


def constancia_template_path():
    folder = os.path.join(
        settings.BASE_DIR,
        'core', 'pos', 'templates', 'frm', 'ctascollect',
    )
    preferred = os.path.join(folder, 'constancia_pago.docx')
    if os.path.isfile(preferred):
        return preferred
    for name in os.listdir(folder):
        low = name.lower()
        if low.endswith('.docx') and 'constancia' in low and 'pago' in low:
            return os.path.join(folder, name)
    return preferred


DOCX_CONTENT_TYPE = (
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
)

CONSTANCIA_COMPANY_DEFAULTS = {
    'legal_name': 'TERRAFIRMA ASESORIA & CONSULTORIA S.A.C.',
    'ruc': '20612888141',
    'address': (
        'JR. UCAYALI MZA. 42 LOTE. 10 (AL COSTADO DE UNCP) '
        'JUNIN - HUANCAYO - EL TAMBO'
    ),
    'mobile': '921047681',
    'website': 'www.Terrafirmaperu.com',
}

_COMPANY_SECTION_MARKERS = (
    'TERRAFIRMA', 'RUC', '20612888141', 'AV.', 'MANCHEGO', 'CELESTINO',
    'CONTACTO', 'UCAYALI', 'HUANCAVELICA', 'HUANCAYO', 'SANEAMIENTO', 'ASESOR',
)


def _format_mobile_pe(mobile):
    digits = re.sub(r'\D', '', mobile or '')
    if len(digits) == 9:
        return '{} {} {}'.format(digits[0:3], digits[3:6], digits[6:9])
    return (mobile or '').strip()


def company_profile_for_constancia(company=None):
    data = dict(CONSTANCIA_COMPANY_DEFAULTS)
    if company:
        if (company.name or '').strip():
            data['legal_name'] = company.name.strip()
        if (company.ruc or '').strip():
            data['ruc'] = company.ruc.strip()
        if (company.address or '').strip():
            data['address'] = company.address.strip()
        mobile_raw = (company.mobile or company.phone or '').strip()
        if mobile_raw:
            digits = re.sub(r'\D', '', mobile_raw)
            data['mobile'] = digits[:9] if len(digits) >= 9 else mobile_raw
        if (company.website or '').strip():
            data['website'] = company.website.strip()
    mobile_fmt = _format_mobile_pe(data['mobile'])
    legal_name = data['legal_name']
    return {
        'legal_name': legal_name,
        'ruc': data['ruc'],
        'address': data['address'],
        'mobile_fmt': mobile_fmt,
        'website': data['website'],
        'footer_line1': data['address'],
        'footer_line2': '{name} RUC: {ruc} - Celular: {mobile}'.format(
            name=legal_name,
            ruc=data['ruc'],
            mobile=mobile_fmt,
        ),
        'display_name': legal_name.upper(),
    }


def _signature_date_plain(payment):
    d = payment.date_joined
    return (
        f'{d.day} de {MONTHS_ES_UPPER.get(d.month, "")} del {d.year}.'
    )


def _signature_date_parts(payment):
    d = payment.date_joined
    month = MONTHS_ES_UPPER.get(d.month, '')
    return [
        '{} '.format(d.day),
        ' {}'.format(month) if month else ' ',
        ' {}'.format(d.year),
    ]


def _soles_en_letras(amount):
    try:
        from num2words import num2words
        n = Decimal(str(amount or 0)).quantize(Decimal('0.01'))
        entero = int(n)
        cents = int((n - entero) * 100)
        words = num2words(entero, lang='es').upper()
        if cents:
            return '{} CON {}/100 SOLES'.format(words, cents)
        return '{} CON 00/100 SOLES'.format(words)
    except Exception:
        return str(amount)


def _payment_method_text(payment):
    method_map = {
        'efectivo': 'EFECTIVO',
        'yape': 'YAPE',
        'plin': 'PLIN',
        'tarjeta_debito_credito': 'TARJETA',
    }
    method_id = getattr(payment, 'payment_method', None) or ''
    if method_id in method_map:
        return method_map[method_id]
    desc = (payment.desc or '').strip()
    if not desc:
        return 'EFECTIVO'
    low = desc.lower()
    for key, label in (
        ('transfer', 'TRANSFERENCIA BANCARIA'),
        ('yape', 'YAPE'),
        ('plin', 'PLIN'),
        ('tarjeta', 'TARJETA'),
        ('efectivo', 'EFECTIVO'),
    ):
        if key in low:
            return label
    return 'EFECTIVO'


def _predio_part(value):
    return (value or '').strip()


def _collector_name_for_constancia(payment):
    payment_collector = getattr(payment, 'collector', None)
    if payment_collector and (payment_collector.name or '').strip():
        return payment_collector.name.strip().upper()
    sale = payment.ctascollect.sale
    collector = getattr(sale, 'collector', None)
    if collector and (collector.name or '').strip():
        return collector.name.strip().upper()
    from core.pos.models import Collector
    return Collector.DEFAULT_NAME.upper()


def _constancia_context(payment):
    ctas = payment.ctascollect
    sale = ctas.sale
    client = sale.client
    user = client.user if client else None
    full_name = (user.get_full_name() if user else '').strip().upper() or 'CLIENTE'
    dni = (user.dni if user else '').strip() or '00000000'
    address = (
        (client.predio_address if client and client.predio_address else '')
        or (client.address if client and client.address else '')
        or '—'
    ).strip()
    district = (
        (client.predio_district if client and client.predio_district else '')
        or (client.district if client and client.district else '')
        or '—'
    ).strip()
    province = (
        (client.predio_province if client and client.predio_province else '')
        or (client.province if client and client.province else '')
        or '—'
    ).strip()
    department = (
        (client.predio_department if client and client.predio_department else '')
        or (client.department if client and client.department else '')
        or '—'
    ).strip()
    total = Decimal(str(ctas.debt or 0))
    quota_label, quota_amount = _resolve_quota_line(payment)
    company = Company.objects.first()
    company_profile = company_profile_for_constancia(company)
    company_name = company_profile['display_name']
    rep_name = company_name
    if sale.employee:
        rep_name = sale.employee.get_full_name().strip().upper() or rep_name
    predio_parts = []
    if client:
        lot = _predio_part(client.predio_lot_number)
        if lot:
            predio_parts.append('LOTE {}'.format(lot))
        block = _predio_part(client.predio_block)
        if block:
            predio_parts.append('MZ. {}'.format(block))
        addr = _predio_part(client.predio_address)
        if addr:
            predio_parts.append(addr)
    predio_desc = ', '.join(predio_parts).upper() if predio_parts else ''
    collector_name = _collector_name_for_constancia(payment)
    return {
        'name': full_name,
        'dni': dni,
        'address': (' ' + address.upper().strip() + ' ') if address and address != '—' else ' — ',
        'district': district,
        'province': province,
        'department': department,
        'total_fmt': f'{total:.2f}',
        'total_words': _soles_en_letras(total),
        'quota_label': quota_label.upper(),
        'quota_amount_fmt': quota_amount,
        'quota_words': _soles_en_letras(quota_amount),
        'payment_method': _payment_method_text(payment),
        'beneficiary': full_name,
        'collector_name': collector_name,
        'company_name': company_profile['legal_name'],
        'rep_name': rep_name,
        'rep_title': 'REPRESENTANTE',
        'signature_date': _signature_date_plain(payment),
        'signature_date_parts': _signature_date_parts(payment),
        'predio_desc': predio_desc,
    }


def _resolve_quota_line(payment):
    desc = (payment.desc or '')
    label_from_desc = None
    m = re.search(r'(\d+\s*(?:ra|da|ta)\s+cuota)', desc, re.I)
    if m:
        label_from_desc = m.group(1)
    ctas = payment.ctascollect
    sale = ctas.sale
    plan = []
    if sale.payment_condition == 'credito':
        n = int(sale.credit_quota_count or 1)
        inicial = Decimal(str(sale.credit_down_payment or 0))
        saldo_cred = Decimal(str(sale.total or 0)) - inicial
        cuota = (saldo_cred / n).quantize(Decimal('0.01')) if n else saldo_cred
        plan.append({'num': 0, 'label': 'inicial', 'amount': f'{inicial:.2f}'})
        for i in range(1, n + 1):
            plan.append({'num': i, 'label': f'{i}ra cuota', 'amount': f'{cuota:.2f}'})
    pay_val = Decimal(str(payment.valor or 0)).quantize(Decimal('0.01'))
    for q in plan:
        if Decimal(str(q.get('amount', 0))).quantize(Decimal('0.01')) == pay_val:
            num = q.get('num')
            if num and num > 0:
                suffix = 'ra' if num in (1, 3) else ('da' if num == 2 else 'ta')
                return '{}{}'.format(num, suffix.upper()), q.get('amount', f'{payment.valor:.2f}')
    label = label_from_desc or (payment.desc or 'CUOTA')
    return label.upper(), f'{pay_val:.2f}'


def _client_code_for_payment(payment):
    client = payment.ctascollect.sale.client
    if not client:
        return ''
    return (client.client_code or '').strip()


def _contract_code_for_payment(payment):
    sale = payment.ctascollect.sale
    return (sale.contract_code or 'CT-{:06d}'.format(sale.pk)).strip()


def _sale_code_for_payment(payment):
    sale = payment.ctascollect.sale
    return (sale.sale_code or 'VT-{:06d}'.format(sale.pk)).strip()


def build_constancia_docx(template_bytes, payment):
    """Genera .docx: correlativo global, barcode abajo (cliente-contrato-venta), diseño intacto."""
    constancia_number = payment.allocate_constancia_number()
    client_code = _client_code_for_payment(payment)
    contract_code = _contract_code_for_payment(payment)
    sale_code = _sale_code_for_payment(payment)
    ctx = _constancia_context(payment)

    if Document is None:
        logger.error('python-docx no instalado; no se puede generar constancia Word.')
        raise RuntimeError(
            'Falta python-docx. Ejecute: pip install python-docx python-barcode Pillow'
        )

    header_parts = prepare_header_footer_parts(template_bytes)

    try:
        doc = Document(BytesIO(template_bytes))
        fill_constancia_doc_paragraphs(doc, ctx)
        body_buf = BytesIO()
        doc.save(body_buf)
        merged = merge_docx_with_template_headers(
            body_buf.getvalue(),
            template_bytes,
            header_parts,
        )
        return decorate_constancia_docx(
            merged,
            client_code,
            contract_code,
            sale_code,
            constancia_number,
        )
    except Exception as exc:
        logger.exception('Error generando constancia Word: %s', exc)
        filled = decorate_constancia_docx(
            template_bytes,
            client_code,
            contract_code,
            sale_code,
            constancia_number,
        )
        try:
            doc = Document(BytesIO(filled))
            fill_constancia_doc_paragraphs(doc, ctx)
            out = BytesIO()
            doc.save(out)
            return decorate_constancia_docx(
                out.getvalue(),
                client_code,
                contract_code,
                sale_code,
                constancia_number,
            )
        except Exception:
            return filled
