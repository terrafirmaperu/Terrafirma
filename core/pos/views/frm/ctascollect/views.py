import json
import os
import re
from decimal import Decimal

from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.template.loader import get_template
from django.urls import reverse_lazy
from django.views.generic import DeleteView, CreateView, FormView
from django.views.generic.base import View
from weasyprint import HTML, CSS

from config import settings
from core.pos.brand_assets import comprobante_print_context
from core.pos.forms import PaymentsCtaCollectForm
from core.pos.mixins import CashRegisterRequiredMixin
from core.pos.models import CashRegisterSession, CtasCollect, PaymentsCtaCollect, Company
from core.pos.views.frm.ctascollect.payment_constancia import (
    DOCX_CONTENT_TYPE,
    build_constancia_docx,
    constancia_template_path,
)
from core.reports.forms import ReportForm
from core.security.mixins import PermissionMixin, SupervisorDeleteApprovalMixin

_CTACOLLECT_PAY_METHOD_LABELS = {
    'efectivo': 'Efectivo',
    'yape': 'Yape',
    'plin': 'Plin',
    'tarjeta_debito_credito': 'Tarjeta',
}
_QUOTA_PAY_METHODS = frozenset(('efectivo', 'yape', 'plin'))


def _parse_quota_payment_method(request):
    """
    Cuota desde el modal: payment_method obligatorio (efectivo, yape o plin).
    Registro genérico sin ese campo: mantiene efectivo por compatibilidad.
    """
    if 'payment_method' not in request.POST:
        return 'efectivo', None
    method = (request.POST.get('payment_method') or '').strip()
    if method not in _QUOTA_PAY_METHODS:
        return None, 'Seleccione la forma de pago: Efectivo, Yape o Plin.'
    return method, None


def _payment_desc_with_method(desc, method):
    base = re.sub(r'\s*\([^)]*\)\s*$', '', (desc or '').strip()).strip()
    if not base:
        base = 'Sin detalles'
    label = _CTACOLLECT_PAY_METHOD_LABELS.get(method, method)
    return '{} ({})'.format(base, label)


class CtasCollectListView(CashRegisterRequiredMixin, PermissionMixin, FormView):
    template_name = 'frm/ctascollect/list.html'
    permission_required = 'view_ctascollect'
    form_class = ReportForm

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST['action']
        try:
            if action == 'search':
                data = []
                search = CtasCollect.objects.select_related(
                    'sale__client__user',
                ).prefetch_related(
                    'sale__saledetail_set__product',
                    'sale__client__properties',
                ).all()
                start_date = request.POST.get('start_date', '')
                end_date = request.POST.get('end_date', '')
                if start_date and end_date:
                    search = search.filter(date_joined__range=[start_date, end_date])
                for a in search.order_by('-id'):
                    data.append(a.toJSON())
            elif action == 'search_pays':
                data = []
                pos = 1
                for det in PaymentsCtaCollect.objects.filter(ctascollect_id=request.POST['id']).order_by('id'):
                    item = det.toJSON()
                    item['pos'] = pos
                    data.append(item)
                    pos += 1
            elif action == 'delete_pay':
                id = request.POST['id']
                det = PaymentsCtaCollect.objects.get(pk=id)
                ctascollect = det.ctascollect
                det.delete()
                ctascollect.validate_debt()
            else:
                data['error'] = 'No ha ingresado una opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Listado de Cuentas por Cobrar'
        context['create_url'] = reverse_lazy('ctascollect_create')
        return context


class CtasCollectCreateView(CashRegisterRequiredMixin, PermissionMixin, CreateView):
    model = CtasCollect
    template_name = 'frm/ctascollect/create.html'
    form_class = PaymentsCtaCollectForm
    success_url = reverse_lazy('ctascollect_list')
    permission_required = 'add_ctascollect'

    def post(self, request, *args, **kwargs):
        action = request.POST['action']
        data = {}
        try:
            if action == 'search_ctascollect':
                data = []
                term = request.POST['term']
                for i in CtasCollect.objects.filter(Q(sale__client__user__first_name__icontains=term) | Q(
                        sale__client__user__last_name__icontains=term) | Q(
                    sale__client__user__dni__icontains=term)
                                                    ).exclude(state=False)[0:10]:
                    item = i.toJSON()
                    item['text'] = i.__str__()
                    data.append(item)
            elif action == 'add':
                with transaction.atomic():
                    payment = PaymentsCtaCollect()
                    payment.ctascollect_id = int(request.POST['ctascollect'])
                    payment.date_joined = request.POST['date_joined']
                    try:
                        amount = Decimal(str(request.POST.get('valor', '0') or '0'))
                    except Exception:
                        amount = Decimal('0')
                    if amount <= 0:
                        data['error'] = 'El monto del pago debe ser mayor a 0.'
                        return HttpResponse(json.dumps(data), content_type='application/json')
                    ctas = CtasCollect.objects.select_for_update().get(pk=payment.ctascollect_id)
                    saldo_actual = Decimal(str(ctas.saldo or 0))
                    if amount > saldo_actual:
                        data['error'] = 'El pago no puede exceder el saldo pendiente.'
                        return HttpResponse(json.dumps(data), content_type='application/json')
                    payment.valor = float(amount)
                    method, method_error = _parse_quota_payment_method(request)
                    if method_error:
                        data['error'] = method_error
                        return HttpResponse(json.dumps(data), content_type='application/json')
                    payment.payment_method = method
                    payment.desc = _payment_desc_with_method(request.POST.get('desc'), method)
                    payment.cash_register_session = CashRegisterSession.get_open_session()
                    payment.save()
                    payment.ctascollect.validate_debt()
                    data = {
                        'id': payment.id,
                        'ctascollect_id': payment.ctascollect_id,
                    }
            else:
                data['error'] = 'No ha ingresado una opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context['list_url'] = self.success_url
        context['title'] = 'Nuevo registro de un Pago'
        context['action'] = 'add'
        return context


class CtasCollectDeleteView(SupervisorDeleteApprovalMixin, CashRegisterRequiredMixin, PermissionMixin, DeleteView):
    model = CtasCollect
    template_name = 'frm/ctascollect/delete.html'
    success_url = reverse_lazy('ctascollect_list')
    permission_required = 'delete_ctascollect'

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            self.get_object().delete()
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Notificación de eliminación'
        context['list_url'] = self.success_url
        return context


class CtasCollectPaymentPrintView(PermissionMixin, View):
    permission_required = 'view_ctascollect'

    def get_success_url(self):
        return reverse_lazy('ctascollect_list')

    def get(self, request, *args, **kwargs):
        try:
            payment = PaymentsCtaCollect.objects.select_related(
                'ctascollect__sale__client__user',
                'ctascollect__sale__employee',
            ).get(pk=self.kwargs['pk'])
            voucher = (self.kwargs.get('voucher') or 'ticket').lower()
            if voucher in ('factura', 'constancia'):
                template_path = constancia_template_path()
                if not os.path.isfile(template_path):
                    return HttpResponse(
                        'No existe la plantilla Word de constancia de pago en templates/frm/ctascollect/.',
                        status=500,
                        content_type='text/plain; charset=utf-8',
                    )
                with open(template_path, 'rb') as f:
                    template_bytes = f.read()
                if not template_bytes:
                    return HttpResponse(
                        'La plantilla Word de constancia está vacía.',
                        status=500,
                        content_type='text/plain; charset=utf-8',
                    )
                docx_bytes = build_constancia_docx(template_bytes, payment)
                if not docx_bytes:
                    return HttpResponse(
                        'No se pudo generar el archivo Word.',
                        status=500,
                        content_type='text/plain; charset=utf-8',
                    )
                nro = payment.constancia_number or payment.pk
                filename = 'constancia_pago_{:09d}.docx'.format(int(nro))
                response = HttpResponse(docx_bytes, content_type=DOCX_CONTENT_TYPE)
                response['Content-Disposition'] = (
                    'attachment; filename="{}"'.format(filename)
                )
                response['Content-Length'] = len(docx_bytes)
                return response
            if voucher != 'ticket':
                voucher = 'ticket'
            template = get_template('frm/ctascollect/print_{}.html'.format(voucher))
            context = {
                'company': Company.objects.first(),
                'payment': payment,
                'ctas': payment.ctascollect,
                'sale': payment.ctascollect.sale,
                **comprobante_print_context(),
            }
            html_template = template.render(context).encode(encoding='UTF-8')
            url_css = os.path.join(
                settings.BASE_DIR,
                'static/lib/bootstrap-4.6.0/css/bootstrap.min.css',
            )
            pdf_file = HTML(
                string=html_template,
                base_url=request.build_absolute_uri(),
            ).write_pdf(stylesheets=[CSS(url_css)], presentational_hints=True)
            return HttpResponse(pdf_file, content_type='application/pdf')
        except PaymentsCtaCollect.DoesNotExist:
            return HttpResponse(
                'Pago no encontrado.',
                status=404,
                content_type='text/plain; charset=utf-8',
            )
        except Exception as exc:
            return HttpResponse(
                'Error al generar el comprobante: {}'.format(exc),
                status=500,
                content_type='text/plain; charset=utf-8',
            )
