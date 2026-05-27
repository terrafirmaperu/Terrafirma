import json
from decimal import Decimal

from django.contrib import messages
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, FormView, UpdateView
from django.utils import timezone

from core.pos.forms import CashRegisterSessionCloseForm, CashRegisterSessionOpenForm
from core.pos.models import CashRegisterSession, PaymentsCtaCollect, Sale
from core.reports.forms import ReportForm
from core.security.mixins import PermissionMixin, SupervisorDeleteApprovalMixin


def _sale_net_cash_in_drawer(sale):
    """
    Efectivo neto que queda en caja por una venta (tras devolver vuelto).
    No incluye Yape/Plin/tarjeta (van en otros buckets del resumen).
    """
    if sale.payment_condition == 'credito':
        if Decimal(str(sale.credit_down_payment or 0)) <= 0:
            return Decimal('0.00')
        if (sale.credit_down_payment_method or 'efectivo') == 'efectivo':
            return Decimal(str(sale.credit_down_payment))
        return Decimal('0.00')
    if sale.payment_method == 'efectivo':
        c = Decimal(str(sale.cash or 0))
        ch = Decimal(str(sale.change or 0))
        return c - ch
    if sale.payment_method == 'efectivo_tarjeta':
        c = Decimal(str(sale.cash or 0))
        ch = Decimal(str(sale.change or 0))
        return c - ch
    return Decimal('0.00')


class CashRegisterSessionListView(PermissionMixin, FormView):
    template_name = 'frm/cash/list.html'
    permission_required = 'view_cashregistersession'
    form_class = ReportForm

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST['action']
        try:
            if action == 'search':
                data = []
                search = CashRegisterSession.objects.all()
                start_date = request.POST.get('start_date', '')
                end_date = request.POST.get('end_date', '')
                if start_date and end_date:
                    search = search.filter(opened_at__date__range=[start_date, end_date])
                for row in search.order_by('-opened_at', '-id'):
                    data.append(row.toJSON())
            elif action == 'cash_resume':
                today = timezone.localdate()
                # Solo la sesión abierta por el usuario actual (relevo: cada cajero ve su turno).
                session = CashRegisterSession.objects.filter(
                    user_opened=request.user,
                    status=CashRegisterSession.OPEN,
                ).order_by('-opened_at').first()

                empty_sales = {
                    'count': 0,
                    'total': '0.00',
                    'cash': '0.00',
                    'yape': '0.00',
                    'plin': '0.00',
                    'tarjeta': '0.00',
                    'mixto_tarjeta': '0.00',
                    'card': '0.00',
                }

                if session is None:
                    data = {
                        'report_date': today.strftime('%Y-%m-%d'),
                        'session': None,
                        'scope': 'sesion',
                        'scope_message': (
                            'Sin caja abierta para su usuario. Abra caja para iniciar un turno; '
                            'los totales quedarán en cero hasta entonces.'
                        ),
                        'sales': empty_sales,
                        'payments': {
                            'count': 0,
                            'total': '0.00',
                        },
                    }
                else:
                    opener = session.user_opened.get_full_name() if session.user_opened_id else ''
                    session_payload = {
                        'id': session.id,
                        'opened_at': session.opened_at.strftime('%Y-%m-%d %H:%M:%S') if session.opened_at else '',
                        'close_at': session.close_at.strftime('%Y-%m-%d %H:%M:%S') if session.close_at else '',
                        'status': session.get_status_display(),
                        'opening_amount': format(session.opening_amount or 0, '.2f'),
                        'user_opened_name': opener,
                    }

                    sales = Sale.objects.filter(cash_register_session=session)
                    # La cuota inicial ya está reflejada en la venta (efectivo/yape/tarjeta); no duplicar en "Pagos".
                    pays = PaymentsCtaCollect.objects.filter(
                        cash_register_session=session,
                    ).exclude(desc__startswith='Cuota inicial')

                    sales_total = sum((Decimal(str(i.total or 0)) for i in sales), Decimal('0.00'))
                    sales_cash = sum((_sale_net_cash_in_drawer(i) for i in sales), Decimal('0.00'))
                    sales_yape = sum(
                        (
                            Decimal(str(i.total or 0))
                            for i in sales
                            if i.payment_condition == 'contado' and i.payment_method == 'yape'
                        ),
                        Decimal('0.00'),
                    )
                    sales_yape += sum(
                        (
                            Decimal(str(i.credit_down_payment or 0))
                            for i in sales
                            if i.payment_condition == 'credito'
                            and Decimal(str(i.credit_down_payment or 0)) > 0
                            and getattr(i, 'credit_down_payment_method', 'efectivo') == 'yape'
                        ),
                        Decimal('0.00'),
                    )
                    sales_plin = sum(
                        (
                            Decimal(str(i.total or 0))
                            for i in sales
                            if i.payment_condition == 'contado' and i.payment_method == 'plin'
                        ),
                        Decimal('0.00'),
                    )
                    sales_plin += sum(
                        (
                            Decimal(str(i.credit_down_payment or 0))
                            for i in sales
                            if i.payment_condition == 'credito'
                            and Decimal(str(i.credit_down_payment or 0)) > 0
                            and getattr(i, 'credit_down_payment_method', 'efectivo') == 'plin'
                        ),
                        Decimal('0.00'),
                    )
                    sales_tarjeta_pure = Decimal('0.00')
                    sales_mixto_tarjeta = Decimal('0.00')
                    for i in sales:
                        if i.payment_condition == 'contado' and i.payment_method == 'tarjeta_debito_credito':
                            sales_tarjeta_pure += Decimal(str(i.total or 0))
                        elif i.payment_condition == 'contado' and i.payment_method == 'efectivo_tarjeta':
                            sales_mixto_tarjeta += Decimal(str(i.amount_debited or 0))
                        elif (
                            i.payment_condition == 'credito'
                            and Decimal(str(i.credit_down_payment or 0)) > 0
                            and getattr(i, 'credit_down_payment_method', '') == 'tarjeta_debito_credito'
                        ):
                            sales_tarjeta_pure += Decimal(
                                str(i.amount_debited or i.credit_down_payment or 0)
                            )

                    sales_card = sales_tarjeta_pure + sales_mixto_tarjeta
                    pays_total = sum((Decimal(str(i.valor or 0)) for i in pays), Decimal('0.00'))

                    data = {
                        'report_date': today.strftime('%Y-%m-%d'),
                        'session': session_payload,
                        'scope': 'sesion',
                        'scope_message': (
                            'Totales del turno actual — sesión de caja n.º {} ({}). '
                            'Solo ventas y cobros registrados mientras esta caja está abierta; '
                            'al cerrar y abrir de nuevo, aquí vuelve a cero.'
                        ).format(session.id, opener or 'cajero'),
                        'sales': {
                            'count': sales.count(),
                            'total': format(sales_total, '.2f'),
                            'cash': format(sales_cash, '.2f'),
                            'yape': format(sales_yape, '.2f'),
                            'plin': format(sales_plin, '.2f'),
                            'tarjeta': format(sales_tarjeta_pure, '.2f'),
                            'mixto_tarjeta': format(sales_mixto_tarjeta, '.2f'),
                            'card': format(sales_card, '.2f'),
                        },
                        'payments': {
                            'count': pays.count(),
                            'total': format(pays_total, '.2f'),
                        },
                    }
            else:
                data['error'] = 'No ha ingresado una opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['create_url'] = reverse_lazy('cashsession_create')
        context['title'] = 'Listado de sesiones de caja'
        return context


class CashRegisterSessionOpenView(PermissionMixin, CreateView):
    model = CashRegisterSession
    template_name = 'frm/cash/create.html'
    form_class = CashRegisterSessionOpenForm
    success_url = reverse_lazy('cashsession_list')
    permission_required = 'add_cashregistersession'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user_open'] = self.request.user
        return kwargs

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST.get('action', '')
        try:
            if action == 'add':
                form = self.get_form()
                data = form.save()
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['list_url'] = self.success_url
        context['title'] = 'Apertura de caja'
        context['action'] = 'add'
        return context


class CashRegisterSessionCloseView(PermissionMixin, UpdateView):
    model = CashRegisterSession
    template_name = 'frm/cash/close.html'
    form_class = CashRegisterSessionCloseForm
    success_url = reverse_lazy('cashsession_list')
    permission_required = 'change_cashregistersession'

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.status != CashRegisterSession.OPEN:
            messages.error(request, 'Esta sesión de caja ya está cerrada.')
            return HttpResponseRedirect(reverse_lazy('cashsession_list'))
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user_close'] = self.request.user
        return kwargs

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST.get('action', '')
        try:
            if action == 'close':
                form = self.get_form()
                data = form.save()
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['list_url'] = self.success_url
        context['title'] = 'Cierre de caja'
        context['action'] = 'close'
        return context


class CashRegisterSessionDeleteView(SupervisorDeleteApprovalMixin, PermissionMixin, DeleteView):
    model = CashRegisterSession
    template_name = 'frm/cash/delete.html'
    success_url = reverse_lazy('cashsession_list')
    permission_required = 'delete_cashregistersession'

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            self.get_object().delete()
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Eliminar sesión de caja'
        context['list_url'] = self.success_url
        return context
