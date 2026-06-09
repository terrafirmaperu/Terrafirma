import json
from decimal import Decimal

from django.contrib import messages
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DeleteView, FormView, UpdateView
from django.utils import timezone

from core.pos.forms import CashRegisterSessionCloseForm, CashRegisterSessionOpenForm
from core.pos.models import CashRegisterSession, Expenses, PaymentsCtaCollect, Sale
from core.reports.forms import ReportForm
from core.security.mixins import PermissionMixin, SupervisorDeleteApprovalMixin


def _session_date_range(session):
    start = timezone.localtime(session.opened_at).date()
    if session.close_at:
        end = timezone.localtime(session.close_at).date()
    else:
        end = timezone.localdate()
    return start, end


def _link_orphan_expenses_to_session(session):
    """Gastos del turno sin sesión asignada (p. ej. creados antes del vínculo)."""
    if session is None:
        return 0
    start, end = _session_date_range(session)
    return Expenses.objects.filter(
        cash_register_session__isnull=True,
        date_joined__range=[start, end],
    ).update(cash_register_session=session)


def _session_expenses_queryset(session):
    if session is None:
        return Expenses.objects.none()
    _link_orphan_expenses_to_session(session)
    return (
        Expenses.objects.select_related('typeexpense')
        .filter(cash_register_session=session)
        .order_by('id')
    )


def _session_expenses_rows(session):
    """Gastos registrados en una sesión de caja."""
    if session is None:
        return []
    rows = []
    for expense in _session_expenses_queryset(session):
        rows.append({
            'id': expense.id,
            'date': expense.date_joined.strftime('%Y-%m-%d'),
            'type': expense.typeexpense.name,
            'concept': expense.get_desc(),
            'amount': format(expense.valor or 0, '.2f'),
            'expenses_url': reverse('expenses_list'),
        })
    return rows


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


def _payment_net_cash_in_drawer(payment):
    if (payment.payment_method or 'efectivo') == 'efectivo':
        return Decimal(str(payment.valor or 0))
    return Decimal('0.00')


def _session_expected_cash_drawer(session):
    """Efectivo estimado en caja: apertura + ingresos en efectivo - gastos."""
    if session is None:
        return Decimal('0.00')
    opening = Decimal(str(session.opening_amount or 0))
    sales = Sale.objects.filter(cash_register_session=session)
    sales_cash = sum((_sale_net_cash_in_drawer(i) for i in sales), Decimal('0.00'))
    pays = PaymentsCtaCollect.objects.filter(
        cash_register_session=session,
    ).exclude(desc__startswith='Cuota inicial')
    pays_cash = sum((_payment_net_cash_in_drawer(i) for i in pays), Decimal('0.00'))
    expenses_total = sum(
        (Decimal(str(i.valor or 0)) for i in _session_expenses_queryset(session)),
        Decimal('0.00'),
    )
    return opening + sales_cash + pays_cash - expenses_total


def _cash_session_expenses_payload(session):
    rows = _session_expenses_rows(session)
    total = sum(
        (Decimal(str(r['amount'])) for r in rows),
        Decimal('0.00'),
    )
    return {
        'session': session.toJSON() if session else None,
        'rows': rows,
        'count': len(rows),
        'total': format(total, '.2f'),
        'expenses_url': reverse('expenses_list'),
        'cash_drawer': {
            'expected': format(_session_expected_cash_drawer(session), '.2f'),
        },
    }


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
                        'expenses': {
                            'count': 0,
                            'total': '0.00',
                            'rows': [],
                        },
                        'cash_drawer': {'expected': '0.00'},
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
                    expenses_qs = _session_expenses_queryset(session)
                    expenses_total = sum(
                        (Decimal(str(i.valor or 0)) for i in expenses_qs),
                        Decimal('0.00'),
                    )

                    data = {
                        'report_date': today.strftime('%Y-%m-%d'),
                        'session': session_payload,
                        'scope': 'sesion',
                        'scope_message': (
                            'Totales del turno actual — sesión de caja n.º {} ({}). '
                            'Los gastos se descuentan del efectivo en caja.'
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
                        'expenses': {
                            'count': expenses_qs.count(),
                            'total': format(expenses_total, '.2f'),
                            'rows': _session_expenses_rows(session),
                        },
                        'cash_drawer': {
                            'expected': format(_session_expected_cash_drawer(session), '.2f'),
                        },
                    }
            elif action in ('cash_session_expenses', 'cash_session_payments'):
                session_id = request.POST.get('session_id', '').strip()
                session = None
                if session_id:
                    session = CashRegisterSession.objects.filter(pk=session_id).first()
                else:
                    session = CashRegisterSession.objects.filter(
                        user_opened=request.user,
                        status=CashRegisterSession.OPEN,
                    ).order_by('-opened_at').first()
                data = _cash_session_expenses_payload(session)
            else:
                data['error'] = 'No ha ingresado una opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['create_url'] = reverse_lazy('cashsession_create')
        context['title'] = 'Listado de sesiones de caja'
        context['expenses_list_url'] = reverse_lazy('expenses_list')
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
            elif action in ('cash_session_expenses', 'cash_session_payments'):
                session = CashRegisterSession.objects.filter(
                    user_opened=request.user,
                    status=CashRegisterSession.OPEN,
                ).order_by('-opened_at').first()
                data = _cash_session_expenses_payload(session)
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
        context['expenses_list_url'] = reverse_lazy('expenses_list')
        context['cash_session_expenses_url'] = reverse_lazy('cashsession_create')
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
            elif action in ('cash_session_expenses', 'cash_session_payments'):
                data = _cash_session_expenses_payload(self.object)
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
        context['expenses_list_url'] = reverse_lazy('expenses_list')
        context['cash_session_expenses_url'] = reverse_lazy(
            'cashsession_close',
            kwargs={'pk': self.object.pk},
        )
        context['cash_session_id'] = self.object.pk
        context['cash_drawer_expected'] = format(
            _session_expected_cash_drawer(self.object),
            '.2f',
        )
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
