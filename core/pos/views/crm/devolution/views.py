import json
import time
from decimal import Decimal

from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.views.generic import DeleteView, CreateView, FormView

from core.pos.forms import *
from core.reports.forms import ReportForm
from core.security.mixins import (
    PermissionMixin,
    SupervisorDeleteApprovalMixin,
    SUPERVISOR_DELETE_SESSION_KEY,
    SUPERVISOR_DELETE_WINDOW_SEC,
)


def _sale_search_results(term):
    term = (term or '').strip()
    qs = Sale.objects.select_related('client__user').filter(is_voided=False)
    if term:
        q = (
            Q(client__user__first_name__icontains=term)
            | Q(client__user__last_name__icontains=term)
            | Q(client__user__dni__icontains=term)
            | Q(sale_code__icontains=term)
            | Q(contract_code__icontains=term)
        )
        if term.isdigit():
            q |= Q(id=int(term))
        qs = qs.filter(q)
    data = []
    for sale in qs.order_by('-id')[:20]:
        item = sale.toJSON()
        item['text'] = '{} · {} · {} · {}'.format(
            sale.sale_code or 'VT-{:06d}'.format(sale.pk),
            sale.contract_code or 'Sin contrato',
            sale.client.user.get_full_name() if sale.client_id else 'Consumidor final',
            sale.client.user.dni if sale.client_id else '',
        )
        data.append(item)
    return data


def _sale_paid_amount(sale):
    if sale.payment_condition == 'credito':
        ctas = CtasCollect.objects.filter(sale=sale).order_by('id').first()
        if ctas:
            paid = Decimal(str(ctas.debt or 0)) - Decimal(str(ctas.saldo or 0))
            return max(Decimal('0.00'), paid.quantize(Decimal('0.01')))
        return Decimal(str(sale.credit_down_payment or 0)).quantize(Decimal('0.01'))
    return Decimal(str(sale.total or 0)).quantize(Decimal('0.01'))


def _consume_refund_authorization(request):
    ts = request.session.get(SUPERVISOR_DELETE_SESSION_KEY)
    now = time.time()
    if ts is None:
        return False, 'Autorización de supervisor requerida para retornar dinero en caja.'
    try:
        ts = float(ts)
    except (TypeError, ValueError):
        return False, 'Autorización inválida.'
    if now - ts > SUPERVISOR_DELETE_WINDOW_SEC:
        return False, 'La autorización del supervisor expiró. Vuelva a intentar.'
    del request.session[SUPERVISOR_DELETE_SESSION_KEY]
    request.session.modified = True
    return True, None


class DevolutionListView(PermissionMixin, FormView):
    template_name = 'crm/devolution/list.html'
    permission_required = 'view_devolution'
    form_class = ReportForm

    def get_form(self, form_class=None):
        form = ReportForm()
        form.fields['sale'].choices = [('', '-------')]
        return form

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST['action']
        try:
            if action == 'search':
                data = []
                search = Devolution.objects.filter()
                start_date = request.POST['start_date']
                end_date = request.POST['end_date']
                sale = request.POST['sale']
                if len(start_date) and len(end_date):
                    search = search.filter(date_joined__range=[start_date, end_date])
                if len(sale):
                    search = search.filter(saledetail__sale_id=sale)
                for a in search:
                    item = a.toJSON()
                    item['saledetail']['sale'] = a.saledetail.sale.toJSON()
                    data.append(item)
            elif action == 'search_sale':
                data = _sale_search_results(request.POST.get('term', ''))
            else:
                data['error'] = 'No ha ingresado una opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Listado de Cancelaciones'
        context['create_url'] = reverse_lazy('devolution_create')
        return context


class DevolutionCreateView(PermissionMixin, CreateView):
    model = Devolution
    template_name = 'crm/devolution/create.html'
    form_class = DevolutionForm
    success_url = reverse_lazy('devolution_list')
    permission_required = 'add_devolution'

    def post(self, request, *args, **kwargs):
        action = request.POST['action']
        data = {}
        try:
            if action == 'search_sale':
                data = _sale_search_results(request.POST.get('term', ''))
            elif action == 'search_products_detail':
                data = []
                for d in SaleDetail.objects.select_related('product').filter(sale_id=request.POST['id'], cant__gt=0):
                    item = d.toJSON()
                    item['amount_return'] = 0
                    item['state'] = 0
                    item['motive'] = ''
                    data.append(item)
            elif action == 'sale_payment_summary':
                sale = Sale.objects.get(pk=int(request.POST.get('sale') or 0))
                paid = _sale_paid_amount(sale)
                data = {
                    'sale_id': sale.id,
                    'sale_code': sale.sale_code or 'VT-{:06d}'.format(sale.pk),
                    'contract_code': sale.contract_code or '',
                    'client': sale.client.user.get_full_name() if sale.client_id else 'Consumidor final',
                    'paid_amount': format(paid, '.2f'),
                    'requires_authorization': paid > 0,
                }
            elif action == 'add':
                with transaction.atomic():
                    sale = Sale.objects.select_for_update().get(pk=int(request.POST.get('sale') or 0))
                    paid = _sale_paid_amount(sale)
                    if paid > 0:
                        ok, auth_error = _consume_refund_authorization(request)
                        if not ok:
                            data['error'] = auth_error
                            return HttpResponse(json.dumps(data), content_type='application/json')
                    products = json.loads(request.POST['products'])
                    if not products:
                        raise ValueError('Debe seleccionar al menos un item para cancelar.')
                    for p in products:
                        amount_return = int(p.get('amount_return') or 0)
                        motive = (p.get('motive') or '').strip()
                        if amount_return <= 0:
                            raise ValueError('La cantidad a cancelar debe ser mayor a 0.')
                        if not motive:
                            raise ValueError('Ingrese el motivo de la cancelación.')
                        detail = SaleDetail.objects.select_for_update().select_related('sale').get(pk=int(p['id']))
                        if amount_return > detail.cant:
                            raise ValueError('La cantidad a cancelar no puede superar la cantidad vendida.')
                        devolution = Devolution()
                        devolution.saledetail = detail
                        devolution.date_joined = request.POST.get('date_joined') or devolution.date_joined
                        devolution.cant = amount_return
                        devolution.motive = motive
                        devolution.save()
                        detail.cant -= amount_return
                        detail.save()
                        detail.sale.calculate_invoice()
            else:
                data['error'] = 'No ha ingresado una opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context['list_url'] = self.success_url
        context['title'] = 'Nuevo registro de una Cancelación'
        context['action'] = 'add'
        return context


class DevolutionDeleteView(SupervisorDeleteApprovalMixin, PermissionMixin, DeleteView):
    model = Devolution
    template_name = 'crm/devolution/delete.html'
    success_url = reverse_lazy('devolution_list')
    permission_required = 'delete_devolution'

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            with transaction.atomic():
                obj = self.get_object()
                detail = SaleDetail.objects.select_for_update().select_related('sale').get(pk=obj.saledetail_id)
                detail.cant += obj.cant
                detail.save()
                sale = detail.sale
                obj.delete()
                sale.calculate_invoice()
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Notificación de eliminación'
        context['list_url'] = self.success_url
        return context
