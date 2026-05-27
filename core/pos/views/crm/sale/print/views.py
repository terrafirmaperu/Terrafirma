import copy
import os
import re
from datetime import datetime
from io import BytesIO
from zipfile import ZipFile, ZIP_DEFLATED
from xml.sax.saxutils import escape
import xml.etree.ElementTree as ET
from decimal import Decimal

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, HttpResponseRedirect
from django.template.loader import get_template
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic.base import View
from weasyprint import HTML, CSS

from config import settings
from core.pos.client_properties import lock_client_properties_for_sale_contract
from core.pos.models import Sale, Company
from core.pos.views.crm.sale.print.contract_docx_decorate import decorate_contract_celia_docx
from core.pos.views.crm.sale.print.docx_codes import decorate_contract_docx


def _contract_code_for_documents(sale):
    return (sale.contract_code or f'CT-{sale.pk:06d}').strip()


def _company_website_text():
    c = Company.objects.first()
    return (c.website or '').strip() if c else ''


def _company_description_text():
    """Descripción corta para el texto bajo el QR del contrato (campo desc en Empresa)."""
    c = Company.objects.first()
    return (c.desc or '').strip() if c else ''


def _client_code_for_sale(sale):
    client = sale.client
    if not client:
        return ''
    return (client.client_code or '').strip()


def _sale_code_for_sale(sale):
    return (sale.sale_code or f'VT-{sale.pk:06d}').strip()


def _is_celia_contract_template(template_path):
    if not template_path:
        return False
    low = os.path.basename(template_path).lower()
    return 'celia' in low


def _build_decorated_contract_docx(template_bytes, sale, mapping, signature_date_plain, template_path=None):
    docx_out = _apply_mapping_to_docx(
        template_bytes,
        mapping,
        signature_date_plain=signature_date_plain,
        location_ctx=_contract_location_ctx(sale) if _is_celia_contract_template(template_path) else None,
    )
    if _is_celia_contract_template(template_path):
        return decorate_contract_celia_docx(
            docx_out,
            _client_code_for_sale(sale),
            _sale_code_for_sale(sale),
            _contract_code_for_documents(sale),
        )
    return decorate_contract_docx(
        docx_out,
        _contract_code_for_documents(sale),
        _company_website_text(),
        _company_description_text(),
    )


MONTHS_ES_UPPER = {
    1: 'ENERO',
    2: 'FEBRERO',
    3: 'MARZO',
    4: 'ABRIL',
    5: 'MAYO',
    6: 'JUNIO',
    7: 'JULIO',
    8: 'AGOSTO',
    9: 'SEPTIEMBRE',
    10: 'OCTUBRE',
    11: 'NOVIEMBRE',
    12: 'DICIEMBRE',
}

W_NS = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
W_P = '{%s}p' % W_NS
W_R = '{%s}r' % W_NS
W_T = '{%s}t' % W_NS
W_PPR = '{%s}pPr' % W_NS
W_RPR = '{%s}rPr' % W_NS
XML_SPACE = '{http://www.w3.org/XML/1998/namespace}space'

_MONTH_NAMES_RE = (
    'enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre|'
    'ENERO|FEBRERO|MARZO|ABRIL|MAYO|JUNIO|JULIO|AGOSTO|SEPTIEMBRE|OCTUBRE|NOVIEMBRE|DICIEMBRE'
)
_SIGNATURE_FIRMA_DATE_RE = re.compile(
    rf'(,\s*)?(\d{{1,2}}\s+de\s+(?:{_MONTH_NAMES_RE})\s+del\s+\d{{4}}\.?)',
    re.IGNORECASE,
)


def _contract_template_path():
    folder = os.path.join(
        settings.BASE_DIR,
        'core', 'pos', 'templates', 'contracts',
    )
    for name in (
        'contrato_Celia.docx',
        'CONTRATO SRA. CELIA.docx',
        'contrato_base.docx',
    ):
        path = os.path.join(folder, name)
        if os.path.isfile(path):
            return path
    return os.path.join(folder, 'contrato_Celia.docx')


def _ajax_request(request):
    return request.headers.get('X-Requested-With') == 'XMLHttpRequest'


def _contract_download_error_response(request, message, status=500):
    if _ajax_request(request):
        return HttpResponse(message, status=status, content_type='text/plain; charset=utf-8')
    try:
        if (
            getattr(request, 'user', None)
            and request.user.is_authenticated
            and request.user.is_client()
        ):
            return HttpResponseRedirect(reverse_lazy('sale_client_list'))
    except Exception:
        pass
    return HttpResponseRedirect(reverse_lazy('sale_admin_list'))


def _contract_signature_date_plain(sale):
    sale_day = sale.date_joined
    contract_date = sale_day.date() if hasattr(sale_day, 'date') else sale_day
    return (
        f'{contract_date.day} de {MONTHS_ES_UPPER.get(contract_date.month, "")} '
        f'del {contract_date.year}.'
    )


def _paragraph_join_text(p_elem):
    parts = []
    for t_elem in p_elem.findall('.//{%s}t' % W_NS):
        if t_elem.text:
            parts.append(t_elem.text)
    return ''.join(parts)


def _clone_run_properties_from_paragraph(p_elem):
    """
    Copia w:rPr de un run del párrafo para no perder fuente (p. ej. Arial Narrow), tamaño ni negrita.
    Prioriza el run con el fragmento de texto más largo (suele ser el cuerpo de la frase).
    """
    runs = p_elem.findall('.//{%s}r' % W_NS)
    best_rpr = None
    best_len = -1
    for r in runs:
        t = r.find(W_T)
        ln = len(t.text) if t is not None and t.text else 0
        rpr = r.find(W_RPR)
        if rpr is not None and ln >= best_len:
            best_len = ln
            best_rpr = rpr
    if best_rpr is not None:
        return copy.deepcopy(best_rpr)
    for r in reversed(runs):
        rpr = r.find(W_RPR)
        if rpr is not None:
            return copy.deepcopy(rpr)
    return None


def _paragraph_set_plain_text(p_elem, new_text):
    r_pr_clone = _clone_run_properties_from_paragraph(p_elem)
    p_pr = None
    for child in list(p_elem):
        if child.tag == W_PPR:
            p_pr = child
        p_elem.remove(child)
    if p_pr is not None:
        p_elem.append(p_pr)
    r = ET.Element(W_R)
    if r_pr_clone is not None:
        r.append(r_pr_clone)
    t = ET.Element(W_T)
    t.set(XML_SPACE, 'preserve')
    t.text = new_text
    r.append(t)
    p_elem.append(r)


def _replace_signature_date_in_document_xml(xml_str, new_date_plain):
    """
    Word suele partir '14 de ABRIL del 2026' en varios <w:t>, por eso .replace() no funciona.
    Se localiza el párrafo (p. ej. con 'Huancavelica') y se sustituye la fecha en el texto unido.
    """
    if not new_date_plain:
        return xml_str
    new_date_plain = new_date_plain.strip()

    def _repl(m):
        prefix = m.group(1) if m.group(1) else ', '
        return prefix + new_date_plain

    try:
        root = ET.fromstring(xml_str.encode('utf-8'))
    except ET.ParseError:
        return xml_str

    def _try_paragraphs(predicate):
        for p_elem in root.iter(W_P):
            full = _paragraph_join_text(p_elem)
            if not predicate(full):
                continue
            new_full, n = _SIGNATURE_FIRMA_DATE_RE.subn(_repl, full, count=1)
            if n:
                _paragraph_set_plain_text(p_elem, new_full)
                return True
        return False

    if not _try_paragraphs(lambda s: 'huancavelica' in s.lower()):
        _try_paragraphs(
            lambda s: 'conformidad' in s.lower()
            and ('firman' in s.lower() or 'firma' in s.lower())
        )

    ET.register_namespace('w', W_NS)
    return ET.tostring(root, encoding='unicode', method='xml')


def _contract_location_ctx(sale):
    client = sale.client
    predio_dep = (
        (client.predio_department if client and client.predio_department else '')
        or (client.department if client else '')
        or 'HUANCAVELICA'
    )
    predio_prov = (
        (client.predio_province if client and client.predio_province else '')
        or (client.province if client else '')
        or 'HUANCAVELICA'
    )
    predio_dist = (
        (client.predio_district if client and client.predio_district else '')
        or (client.district if client else '')
        or 'HUANCAVELICA'
    )
    return {
        'district': predio_dist.strip().upper(),
        'province': predio_prov.strip().upper(),
        'department': predio_dep.strip().upper(),
    }


def _contract_signature_date_celia(sale):
    sale_day = sale.date_joined
    contract_date = sale_day.date() if hasattr(sale_day, 'date') else sale_day
    return (
        f'{contract_date.day} de {MONTHS_ES_UPPER.get(contract_date.month, "")} '
        f'del {contract_date.year}'
    )


def _contract_mapping_celia(sale):
    client = sale.client
    user = client.user if client else None
    full_name = (user.get_full_name() if user else '').strip().upper() or 'CLIENTE'
    dni = (user.dni if user else '').strip() or '00000000'
    mobile = (client.mobile if client and client.mobile else '').strip() or '000000000'
    address = (
        (client.predio_address if client and client.predio_address else '')
        or (client.address if client else '')
        or '—'
    ).strip().upper()
    total_amount = Decimal(str(sale.total or 0)).quantize(Decimal('0.01'))
    contract_date_text = _contract_signature_date_celia(sale)

    return {
        'CELIA JUSTINA BUSSO ÑAHUI': escape(full_name),
        '23260963': escape(dni),
        '971895287': escape(mobile),
        'Av. C. Manchego Muñoz N°1162 - BARRIO DE SANTA ANA': escape(address),
        'MONTO TOTAL S/3000.00': escape(f'MONTO TOTAL S/{total_amount:.2f}'),
        'S/3000.00': escape(f'S/{total_amount:.2f}'),
        '15 de MAYO del 2026': escape(contract_date_text),
        '15 de MAYO del 2026.': escape(contract_date_text + '.'),
        'DNI: 23260963': escape(f'DNI: {dni}'),
    }


def _contract_mapping_legacy(sale):
    client = sale.client
    user = client.user if client else None
    full_name = (user.get_full_name() if user else '').strip().upper() or 'CLIENTE'
    dni = (user.dni if user else '').strip() or '00000000'
    mobile = (client.mobile if client and client.mobile else '').strip() or '000000000'
    predio_dep = (client.predio_department if client and client.predio_department else client.department if client else '') or '________________'
    predio_prov = (client.predio_province if client and client.predio_province else client.province if client else '') or '________________'
    predio_dist = (client.predio_district if client and client.predio_district else client.district if client else '') or '________________'
    centro_poblado = (client.predio_address if client and client.predio_address else client.address if client else '') or '________________'
    contract_date_text = _contract_signature_date_plain(sale)

    total_amount = Decimal(str(sale.total or 0)).quantize(Decimal('0.01'))
    down_payment = Decimal('0.00')
    if sale.payment_condition == 'credito':
        down_payment = Decimal(str(sale.credit_down_payment or 0)).quantize(Decimal('0.01'))
    remaining_amount = (total_amount - down_payment).quantize(Decimal('0.01'))
    if remaining_amount < 0:
        remaining_amount = Decimal('0.00')

    return {
        'ELSA AROTOMA HUAMANI': escape(full_name),
        '70360638': escape(dni),
        '979769335': escape(mobile),
        'HUANCAPITE': escape(centro_poblado.upper()),
        'ANDABAMBA': escape(predio_dist.upper()),
        'ACOBAMBA': escape(predio_prov.upper()),
        'HUANCAVELICA': escape(predio_dep.upper()),
        '14 de ABRIL del 2026.': escape(contract_date_text),
        'DE S/ 700.00 SOLES': escape(f'DE S/ {total_amount:.2f} SOLES'),
        'DE S/700.00 SOLES': escape(f'DE S/ {total_amount:.2f} SOLES'),
        'S/75.00 soles': escape(f'S/ {down_payment:.2f} soles'),
        'S/ 75.00 soles': escape(f'S/ {down_payment:.2f} soles'),
        'S/625.00 soles.': escape(f'S/ {remaining_amount:.2f} soles.'),
        'S/ 625.00 soles.': escape(f'S/ {remaining_amount:.2f} soles.'),
    }


def _contract_mapping_from_sale(sale, template_path=None):
    if _is_celia_contract_template(template_path):
        return _contract_mapping_celia(sale)
    return _contract_mapping_legacy(sale)


def _apply_celia_location_replacements(xml_str, location_ctx):
    if not location_ctx:
        return xml_str
    dist = escape(location_ctx['district'])
    prov = escape(location_ctx['province'])
    dept = escape(location_ctx['department'])
    xml_str = xml_str.replace(' HUANCAVELICA, ', ' {} , '.format(dist))
    xml_str = xml_str.replace(' HUANCAVELICA ', ' {} '.format(prov))
    xml_str = xml_str.replace('>HUANCAVELICA</w:t>', '>' + dept + '</w:t>')
    return xml_str


def _apply_mapping_to_docx(template_bytes, mapping, signature_date_plain=None, location_ctx=None):
    zin_mem = BytesIO(template_bytes)
    zout_mem = BytesIO()
    with ZipFile(zin_mem, 'r') as zin, ZipFile(zout_mem, 'w', ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            content = zin.read(item.filename)
            if item.filename.startswith('word/') and item.filename.endswith('.xml'):
                txt = content.decode('utf-8', 'ignore')
                if item.filename == 'word/document.xml' and signature_date_plain:
                    txt = _replace_signature_date_in_document_xml(txt, signature_date_plain)
                for old, new in mapping.items():
                    if old:
                        txt = txt.replace(old, new)
                if location_ctx:
                    txt = _apply_celia_location_replacements(txt, location_ctx)
                content = txt.encode('utf-8')
            zout.writestr(item, content)
    return zout_mem.getvalue()


def _docx_bytes_to_preview_text(docx_bytes):
    with ZipFile(BytesIO(docx_bytes), 'r') as zf:
        xml_bytes = zf.read('word/document.xml')
    root = ET.fromstring(xml_bytes)
    ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    lines = []
    for p in root.findall('.//w:p', ns):
        parts = []
        for t in p.findall('.//w:t', ns):
            parts.append(t.text or '')
        line = ''.join(parts).strip()
        if line:
            lines.append(line)
    return '\n'.join(lines)


def _archive_contract_docx(sale, docx_bytes):
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    archive_dir = os.path.join(settings.MEDIA_ROOT, 'contracts_archive')
    os.makedirs(archive_dir, exist_ok=True)
    cc = (sale.contract_code or f'CT-{sale.id:06d}').replace('/', '-').replace('\\', '-')
    file_name = f'{cc}_{ts}.docx'
    file_path = os.path.join(archive_dir, file_name)
    with open(file_path, 'wb') as f:
        f.write(docx_bytes)
    return file_path


DOCX_CONTENT_TYPE = (
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
)


class SalePrintVoucherView(LoginRequiredMixin, View):
    success_url = reverse_lazy('sale_admin_list')

    def get_success_url(self):
        if self.request.user.is_client():
            return reverse_lazy('sale_client_list')
        return self.success_url

    def get_height_ticket(self):
        sale = Sale.objects.get(pk=self.kwargs['pk'])
        height = 120
        increment = sale.saledetail_set.all().count() * 5.45
        height += increment
        return round(height)

    def get(self, request, *args, **kwargs):
        try:
            sale = Sale.objects.get(pk=self.kwargs['pk'])
            context = {'sale': sale, 'company': Company.objects.first()}
            if sale.type_voucher == 'ticket':
                template = get_template('crm/sale/print/ticket.html')
                context['height'] = self.get_height_ticket()
            else:
                template = get_template('crm/sale/print/invoice.html')
            html_template = template.render(context).encode(encoding="UTF-8")
            url_css = os.path.join(settings.BASE_DIR, 'static/lib/bootstrap-4.6.0/css/bootstrap.min.css')
            pdf_file = HTML(string=html_template, base_url=request.build_absolute_uri()).write_pdf(
                stylesheets=[CSS(url_css)], presentational_hints=True)
            response = HttpResponse(pdf_file, content_type='application/pdf')
            # response['Content-Disposition'] = 'filename="generate_html.pdf"'
            return response
        except:
            pass
        return HttpResponseRedirect(self.get_success_url())


class SalePrintContractView(LoginRequiredMixin, View):
    success_url = reverse_lazy('sale_admin_list')
    raise_exception = True

    def get_success_url(self):
        if self.request.user.is_client():
            return reverse_lazy('sale_client_list')
        return self.success_url

    def get(self, request, *args, **kwargs):
        template_path = _contract_template_path()
        if not os.path.isfile(template_path):
            return _contract_download_error_response(
                request,
                'No existe la plantilla del contrato (contrato_Celia.docx o contrato_base.docx).',
                status=500,
            )
        try:
            sale = Sale.objects.select_related('client__user').get(pk=self.kwargs['pk'])
            mapping = _contract_mapping_from_sale(sale, template_path)
            with open(template_path, 'rb') as f:
                template_bytes = f.read()
            sig_date = (
                _contract_signature_date_celia(sale)
                if _is_celia_contract_template(template_path)
                else _contract_signature_date_plain(sale)
            )
            docx_out = _build_decorated_contract_docx(
                template_bytes,
                sale,
                mapping,
                sig_date,
                template_path=template_path,
            )
            out_name = sale.contract_docx_basename()
            response = HttpResponse(docx_out, content_type=DOCX_CONTENT_TYPE)
            response['Content-Disposition'] = f'attachment; filename="{out_name}"'
            response['X-Contract-Filename'] = out_name
            lock_client_properties_for_sale_contract(sale)
            return response
        except Sale.DoesNotExist:
            return _contract_download_error_response(request, 'Venta no encontrada.', status=404)
        except Exception:
            return _contract_download_error_response(
                request,
                'Error al generar el contrato. Revise datos del cliente y la plantilla Word.',
                status=500,
            )


class SalePrintContractPreviewView(LoginRequiredMixin, View):
    success_url = reverse_lazy('sale_admin_list')

    def get_success_url(self):
        if self.request.user.is_client():
            return reverse_lazy('sale_client_list')
        return self.success_url

    def get(self, request, *args, **kwargs):
        try:
            sale = Sale.objects.select_related('client__user').get(pk=self.kwargs['pk'])
            template_path = _contract_template_path()
            mapping = _contract_mapping_from_sale(sale, template_path)
            with open(template_path, 'rb') as f:
                template_bytes = f.read()
            sig_date = (
                _contract_signature_date_celia(sale)
                if _is_celia_contract_template(template_path)
                else _contract_signature_date_plain(sale)
            )
            docx_out = _build_decorated_contract_docx(
                template_bytes,
                sale,
                mapping,
                sig_date,
                template_path=template_path,
            )
            preview_text = _docx_bytes_to_preview_text(docx_out)
            return render(
                request,
                'crm/sale/print/contract_preview.html',
                {
                    'sale': sale,
                    'preview_text': preview_text,
                    'embed': request.GET.get('embed') == '1',
                },
            )
        except Exception:
            return HttpResponseRedirect(self.get_success_url())


class SalePrintContractQuickView(LoginRequiredMixin, View):
    success_url = reverse_lazy('sale_admin_list')

    def get_success_url(self):
        if self.request.user.is_client():
            return reverse_lazy('sale_client_list')
        return self.success_url

    def get(self, request, *args, **kwargs):
        try:
            sale = Sale.objects.select_related('client__user').get(pk=self.kwargs['pk'])
            template_path = _contract_template_path()
            mapping = _contract_mapping_from_sale(sale, template_path)
            with open(template_path, 'rb') as f:
                template_bytes = f.read()
            sig_date = (
                _contract_signature_date_celia(sale)
                if _is_celia_contract_template(template_path)
                else _contract_signature_date_plain(sale)
            )
            docx_out = _build_decorated_contract_docx(
                template_bytes,
                sale,
                mapping,
                sig_date,
                template_path=template_path,
            )
            _archive_contract_docx(sale, docx_out)
            lock_client_properties_for_sale_contract(sale)
            preview_text = _docx_bytes_to_preview_text(docx_out)
            return render(
                request,
                'crm/sale/print/contract_quick_print.html',
                {'sale': sale, 'preview_text': preview_text},
            )
        except Exception:
            return HttpResponseRedirect(self.get_success_url())
