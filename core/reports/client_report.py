# -*- coding: utf-8 -*-
"""Consultas y serialización para el reporte de clientes."""

import re
from decimal import Decimal

from django.db.models import Prefetch, Q
from django.utils import timezone

from core.pos.models import (
    AdvisoryProgressCase,
    CashRegisterSession,
    Client,
    ClientProperty,
    CtasCollect,
    Devolution,
    PaymentsCtaCollect,
    Product,
    Sale,
    SaleDetail,
)


def _distinct_sorted(values):
    seen = set()
    out = []
    for v in values:
        if not v:
            continue
        key = v.strip().lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(v.strip())
    return sorted(out, key=lambda x: x.lower())


def get_client_report_filter_options():
    """Valores distintos para los filtros del reporte."""
    prop_qs = ClientProperty.objects.all()
    communities = _distinct_sorted(
        prop_qs.filter(community_location_enabled=True)
        .exclude(community='')
        .values_list('community', flat=True)
    )
    population_centers = _distinct_sorted(
        prop_qs.filter(community_location_enabled=True)
        .exclude(population_center='')
        .values_list('population_center', flat=True)
    )
    provinces = _distinct_sorted(
        list(prop_qs.exclude(province='').values_list('province', flat=True))
        + list(Client.objects.exclude(province='').values_list('province', flat=True))
        + list(Client.objects.exclude(predio_province='').values_list('predio_province', flat=True))
    )
    districts = _distinct_sorted(
        list(prop_qs.exclude(district='').values_list('district', flat=True))
        + list(Client.objects.exclude(district='').values_list('district', flat=True))
        + list(Client.objects.exclude(predio_district='').values_list('predio_district', flat=True))
    )
    products = [
        {'id': p.id, 'name': p.name}
        for p in Product.objects.filter(client_properties__isnull=False)
        .distinct()
        .order_by('name')
    ]
    return {
        'communities': communities,
        'population_centers': population_centers,
        'provinces': provinces,
        'districts': districts,
        'products': products,
    }


def filter_clients_report(
    community='',
    population_center='',
    province='',
    district='',
    location_type='',
):
    qs = Client.objects.select_related('user').order_by(
        'user__last_name', 'user__first_name', 'id',
    )
    qs = qs.prefetch_related(
        Prefetch(
            'advisory_cases',
            queryset=AdvisoryProgressCase.objects.select_related('sale').order_by('-id'),
        ),
    )

    if not any([community, population_center, province, district, location_type]):
        return qs

    if location_type == 'community':
        qs = qs.filter(
            properties__community_location_enabled=True,
        ).exclude(properties__community='').distinct()
    elif location_type == 'population_center':
        qs = qs.filter(
            properties__community_location_enabled=True,
        ).exclude(properties__population_center='').distinct()

    if community:
        qs = qs.filter(properties__community__iexact=community.strip()).distinct()
    if population_center:
        qs = qs.filter(
            properties__population_center__iexact=population_center.strip(),
        ).distinct()

    if province:
        p = province.strip()
        qs = qs.filter(
            Q(properties__province__iexact=p)
            | Q(province__iexact=p)
            | Q(predio_province__iexact=p)
        ).distinct()
    if district:
        d = district.strip()
        qs = qs.filter(
            Q(properties__district__iexact=d)
            | Q(district__iexact=d)
            | Q(predio_district__iexact=d)
        ).distinct()

    return qs


def _format_case_process(case):
    stage = 'Etapa {}/{}'.format(case.current_stage, case.total_stages)
    sale = case.sale
    if sale and not getattr(sale, 'is_voided', False):
        code = (sale.contract_code or sale.sale_code or '').strip()
        if code:
            return '{} — {} ({})'.format(case.title, stage, code)
    return '{} — {}'.format(case.title, stage)


def client_process_summary(client):
    cases = list(client.advisory_cases.all())
    if cases:
        return '; '.join(_format_case_process(c) for c in cases)

    active_sales = Sale.objects.filter(
        client=client,
        is_voided=False,
    ).exclude(
        Q(contract_code='') & Q(sale_code=''),
    ).order_by('-id')[:3]
    if active_sales:
        parts = []
        for s in active_sales:
            code = (s.contract_code or s.sale_code or 'Venta #{}'.format(s.id)).strip()
            parts.append('Contrata sin caso — {}'.format(code))
        return '; '.join(parts)
    return 'Sin proceso'


def client_to_report_row(client):
    user = client.user
    return {
        'id': client.id,
        'first_name': user.first_name or '',
        'last_name': user.last_name or '',
        'dni': user.dni or '',
        'mobile': client.mobile or '',
        'process': client_process_summary(client),
    }


def search_clients_report(filters):
    qs = filter_clients_report(
        community=filters.get('community') or '',
        population_center=filters.get('population_center') or '',
        province=filters.get('province') or '',
        district=filters.get('district') or '',
        location_type=filters.get('location_type') or '',
    )
    return [client_to_report_row(c) for c in qs]


def enrollment_summary_report(filters):
    qs = filter_clients_report(
        community=filters.get('community') or '',
        population_center=filters.get('population_center') or '',
        province=filters.get('province') or '',
        district=filters.get('district') or '',
        location_type=filters.get('location_type') or '',
    )
    client_ids = list(qs.values_list('id', flat=True))
    props = ClientProperty.objects.filter(client_id__in=client_ids).select_related('client__user')
    groups = {}
    for prop in props:
        community = (prop.community or 'Sin comunidad').strip() or 'Sin comunidad'
        center = (prop.population_center or 'Sin centro poblado').strip() or 'Sin centro poblado'
        key = (community.upper(), center.upper())
        if key not in groups:
            groups[key] = {
                'community': community.upper(),
                'population_center': center.upper(),
                'clients': set(),
                'properties': 0,
            }
        groups[key]['clients'].add(prop.client_id)
        groups[key]['properties'] += 1

    rows = []
    for item in groups.values():
        rows.append({
            'community': item['community'],
            'population_center': item['population_center'],
            'clients_count': len(item['clients']),
            'properties_count': item['properties'],
        })
    return sorted(rows, key=lambda x: (x['community'], x['population_center']))


def _money(value):
    return format(Decimal(str(value or 0)).quantize(Decimal('0.01')), '.2f')


def _sale_paid_amount_for_report(sale):
    if sale.payment_condition == 'credito':
        return Decimal(str(sale.credit_down_payment or 0)).quantize(Decimal('0.01'))
    return Decimal(str(sale.total or 0)).quantize(Decimal('0.01'))


def _sale_payment_method_for_report(sale):
    if sale.payment_condition == 'credito':
        return sale.get_credit_down_payment_method_display() if sale.credit_down_payment else 'Crédito sin inicial'
    return sale.get_payment_method_display()


def paid_today_report(user):
    today = timezone.localdate()
    session = CashRegisterSession.get_open_session()
    if not session:
        return {
            'session': None,
            'message': 'No hay caja abierta en el sistema. El responsable debe aperturar caja.',
            'rows': [],
            'total': '0.00',
        }

    rows = []
    total = Decimal('0.00')
    sales = (
        Sale.objects.select_related('client__user')
        .filter(cash_register_session=session, date_joined=today, is_voided=False)
        .order_by('id')
    )
    for sale in sales:
        amount = _sale_paid_amount_for_report(sale)
        if amount <= 0:
            continue
        total += amount
        rows.append({
            'date': sale.date_joined.strftime('%Y-%m-%d'),
            'client': sale.client.user.get_full_name() if sale.client_id else 'Consumidor final',
            'dni': sale.client.user.dni if sale.client_id else '',
            'sale_code': sale.sale_code or 'VT-{:06d}'.format(sale.pk),
            'contract_code': sale.contract_code or '',
            'concept': 'Venta' if sale.payment_condition == 'contado' else 'Inicial de crédito',
            'method': _sale_payment_method_for_report(sale),
            'amount': _money(amount),
        })

    payments = (
        PaymentsCtaCollect.objects.select_related('ctascollect__sale__client__user')
        .filter(cash_register_session=session, date_joined=today)
        .exclude(desc__startswith='Cuota inicial')
        .order_by('id')
    )
    for payment in payments:
        sale = payment.ctascollect.sale
        amount = Decimal(str(payment.valor or 0)).quantize(Decimal('0.01'))
        if amount <= 0:
            continue
        total += amount
        rows.append({
            'date': payment.date_joined.strftime('%Y-%m-%d'),
            'client': sale.client.user.get_full_name() if sale.client_id else 'Consumidor final',
            'dni': sale.client.user.dni if sale.client_id else '',
            'sale_code': sale.sale_code or 'VT-{:06d}'.format(sale.pk),
            'contract_code': sale.contract_code or '',
            'concept': payment.desc or 'Pago de cuota',
            'method': payment.get_payment_method_display(),
            'amount': _money(amount),
        })

    return {
        'session': {
            'id': session.id,
            'opened_at': session.opened_at.strftime('%Y-%m-%d %H:%M:%S') if session.opened_at else '',
        },
        'message': 'Pagos del turno actual de caja.',
        'rows': rows,
        'total': _money(total),
    }


def debtors_report(term=''):
    term = (term or '').strip()
    qs = (
        CtasCollect.objects.select_related('sale__client__user')
        .filter(state=True, saldo__gt=0)
        .order_by('-id')
    )
    if term:
        qs = qs.filter(
            Q(sale__client__user__first_name__icontains=term)
            | Q(sale__client__user__last_name__icontains=term)
            | Q(sale__client__user__dni__icontains=term)
            | Q(sale__sale_code__icontains=term)
            | Q(sale__contract_code__icontains=term)
        )
    rows = []
    for cta in qs[:100]:
        sale = cta.sale
        rows.append({
            'client': sale.client.user.get_full_name() if sale.client_id else 'Consumidor final',
            'dni': sale.client.user.dni if sale.client_id else '',
            'sale_code': sale.sale_code or 'VT-{:06d}'.format(sale.pk),
            'contract_code': sale.contract_code or '',
            'total': _money(cta.debt),
            'paid': _money(Decimal(str(cta.debt or 0)) - Decimal(str(cta.saldo or 0))),
            'saldo': _money(cta.saldo),
            'end_date': cta.end_date.strftime('%Y-%m-%d') if cta.end_date else '',
        })
    return rows


def _parse_report_date(value, fallback):
    if not value:
        return fallback
    try:
        return timezone.datetime.strptime(value, '%Y-%m-%d').date()
    except (TypeError, ValueError):
        return fallback


def payments_by_day_report(start_date='', end_date=''):
    today = timezone.localdate()
    start = _parse_report_date(start_date, today)
    end = _parse_report_date(end_date, today)
    if start > end:
        start, end = end, start

    days = {}

    def bucket(day):
        key = day.strftime('%Y-%m-%d')
        if key not in days:
            days[key] = {
                'date': key,
                'count': 0,
                'cash': Decimal('0.00'),
                'yape': Decimal('0.00'),
                'plin': Decimal('0.00'),
                'tarjeta': Decimal('0.00'),
                'total': Decimal('0.00'),
            }
        return days[key]

    sales = Sale.objects.filter(date_joined__range=[start, end], is_voided=False)
    for sale in sales:
        amount = _sale_paid_amount_for_report(sale)
        if amount <= 0:
            continue
        method = sale.credit_down_payment_method if sale.payment_condition == 'credito' else sale.payment_method
        row = bucket(sale.date_joined)
        row['count'] += 1
        if method == 'efectivo':
            row['cash'] += amount
        elif method == 'yape':
            row['yape'] += amount
        elif method == 'plin':
            row['plin'] += amount
        elif method in ('tarjeta_debito_credito', 'efectivo_tarjeta'):
            row['tarjeta'] += amount
        row['total'] += amount

    payments = PaymentsCtaCollect.objects.filter(date_joined__range=[start, end]).exclude(
        desc__startswith='Cuota inicial',
    )
    for payment in payments:
        amount = Decimal(str(payment.valor or 0)).quantize(Decimal('0.01'))
        if amount <= 0:
            continue
        row = bucket(payment.date_joined)
        row['count'] += 1
        if payment.payment_method == 'efectivo':
            row['cash'] += amount
        elif payment.payment_method == 'yape':
            row['yape'] += amount
        elif payment.payment_method == 'plin':
            row['plin'] += amount
        elif payment.payment_method == 'tarjeta_debito_credito':
            row['tarjeta'] += amount
        row['total'] += amount

    return [
        {
            'date': item['date'],
            'count': item['count'],
            'cash': _money(item['cash']),
            'yape': _money(item['yape']),
            'plin': _money(item['plin']),
            'tarjeta': _money(item['tarjeta']),
            'total': _money(item['total']),
        }
        for item in sorted(days.values(), key=lambda x: x['date'])
    ]


def cancellations_report(start_date='', end_date=''):
    today = timezone.localdate()
    start = _parse_report_date(start_date, today)
    end = _parse_report_date(end_date, today)
    if start > end:
        start, end = end, start

    qs = (
        Devolution.objects.select_related(
            'saledetail__sale__client__user',
            'saledetail__product',
        )
        .filter(date_joined__range=[start, end])
        .order_by('-date_joined', '-id')
    )
    rows = []
    for item in qs:
        detail = item.saledetail
        sale = detail.sale
        unit_price = Decimal(str(detail.price or 0)).quantize(Decimal('0.01'))
        estimated = unit_price * Decimal(str(item.cant or 0))
        rows.append({
            'date': item.date_joined.strftime('%Y-%m-%d'),
            'client': sale.client.user.get_full_name() if sale.client_id else 'Consumidor final',
            'dni': sale.client.user.dni if sale.client_id else '',
            'sale_code': sale.sale_code or 'VT-{:06d}'.format(sale.pk),
            'contract_code': sale.contract_code or '',
            'product': detail.product.name if detail.product_id else '',
            'quantity': item.cant,
            'estimated_amount': _money(estimated),
            'motive': item.motive or 'Sin detalles',
        })
    return rows


def _quota_progress_for_cta(cta):
    sale = cta.sale
    n = max(1, int(sale.credit_quota_count or 1))
    inicial = Decimal(str(sale.credit_down_payment or 0)).quantize(Decimal('0.01'))
    paid_toward_quotas = (
        Decimal(str(cta.debt or 0))
        - Decimal(str(cta.saldo or 0))
        - inicial
    )
    if paid_toward_quotas < 0:
        paid_toward_quotas = Decimal('0.00')

    paid_count = 0
    acc = Decimal('0.00')
    for quota in cta.get_quota_plan():
        if int(quota.get('num') or 0) <= 0:
            continue
        acc += Decimal(str(quota.get('amount') or 0)).quantize(Decimal('0.01'))
        if paid_toward_quotas + Decimal('0.0001') >= acc:
            paid_count += 1

    current = min(n, paid_count + 1)
    if Decimal(str(cta.saldo or 0)) <= 0:
        current = n
    return {
        'current': current,
        'total': n,
        'paid_count': paid_count,
        'label': 'Cuota {} / {}'.format(current, n),
    }


def product_enrollment_debt_report(filters):
    qs = filter_clients_report(
        community=filters.get('community') or '',
        population_center=filters.get('population_center') or '',
        province=filters.get('province') or '',
        district=filters.get('district') or '',
        location_type=filters.get('location_type') or '',
    )
    client_ids = list(qs.values_list('id', flat=True))
    props = (
        ClientProperty.objects.select_related('client__user', 'product')
        .filter(client_id__in=client_ids, product__isnull=False)
        .order_by('product__name', 'community', 'population_center', 'client__user__last_name')
    )
    prop_ids = [p.id for p in props]
    details = (
        SaleDetail.objects.select_related('sale__client__user', 'product')
        .filter(client_property_id__in=prop_ids, sale__is_voided=False)
        .order_by('-sale_id')
    )
    sale_by_prop = {}
    for detail in details:
        sale_by_prop.setdefault(detail.client_property_id, detail.sale)

    ctas_by_sale = {
        c.sale_id: c
        for c in CtasCollect.objects.select_related('sale')
        .filter(sale_id__in=[s.id for s in sale_by_prop.values()], saldo__gt=0, state=True)
    }

    summary = {}
    debtors = []
    for prop in props:
        product_name = prop.product.name if prop.product_id else 'Sin producto'
        community = (prop.community or 'Sin comunidad').strip().upper() or 'Sin comunidad'
        center = (prop.population_center or 'Sin centro poblado').strip().upper() or 'Sin centro poblado'
        key = (product_name, community, center)
        if key not in summary:
            summary[key] = {
                'product': product_name,
                'community': community,
                'population_center': center,
                'clients': set(),
                'properties_count': 0,
                'debtors_count': 0,
                'debt_total': Decimal('0.00'),
            }
        summary[key]['clients'].add(prop.client_id)
        summary[key]['properties_count'] += 1

        sale = sale_by_prop.get(prop.id)
        cta = ctas_by_sale.get(sale.id) if sale else None
        if not cta:
            continue
        progress = _quota_progress_for_cta(cta)
        saldo = Decimal(str(cta.saldo or 0)).quantize(Decimal('0.01'))
        summary[key]['debtors_count'] += 1
        summary[key]['debt_total'] += saldo
        debtors.append({
            'product': product_name,
            'community': community,
            'population_center': center,
            'client': sale.client.user.get_full_name() if sale.client_id else 'Consumidor final',
            'dni': sale.client.user.dni if sale.client_id else '',
            'sale_code': sale.sale_code or 'VT-{:06d}'.format(sale.pk),
            'contract_code': sale.contract_code or '',
            'quota': progress['label'],
            'paid_quotas': progress['paid_count'],
            'total_quotas': progress['total'],
            'paid': _money(Decimal(str(cta.debt or 0)) - saldo),
            'saldo': _money(saldo),
            'end_date': cta.end_date.strftime('%Y-%m-%d') if cta.end_date else '',
        })

    summary_rows = []
    for item in summary.values():
        summary_rows.append({
            'product': item['product'],
            'community': item['community'],
            'population_center': item['population_center'],
            'clients_count': len(item['clients']),
            'properties_count': item['properties_count'],
            'debtors_count': item['debtors_count'],
            'debt_total': _money(item['debt_total']),
        })

    return {
        'summary': sorted(summary_rows, key=lambda x: (x['product'], x['community'], x['population_center'])),
        'debtors': sorted(debtors, key=lambda x: (x['product'], x['community'], x['client'])),
    }


def _quota_number_from_text(text):
    text = (text or '').lower()
    m = re.search(r'(\d+)\s*(?:ra|da|ta)?\s*cuota', text)
    if not m:
        return None
    try:
        return int(m.group(1))
    except (TypeError, ValueError):
        return None


def _quota_paid_matrix_for_cta(cta):
    sale = cta.sale
    quota_count = max(1, int(sale.credit_quota_count or 1))
    quota_paid = {i: Decimal('0.00') for i in range(1, quota_count + 1)}
    payments = list(
        PaymentsCtaCollect.objects.filter(ctascollect=cta)
        .exclude(desc__startswith='Cuota inicial')
        .order_by('date_joined', 'id')
    )

    unassigned = []
    for payment in payments:
        amount = Decimal(str(payment.valor or 0)).quantize(Decimal('0.01'))
        if amount <= 0:
            continue
        quota_num = _quota_number_from_text(payment.desc)
        if quota_num and 1 <= quota_num <= quota_count:
            quota_paid[quota_num] += amount
        else:
            unassigned.append(amount)

    if unassigned:
        plan_amounts = {
            int(item['num']): Decimal(str(item['amount'])).quantize(Decimal('0.01'))
            for item in cta.get_quota_plan()
            if int(item.get('num') or 0) > 0
        }
        current_quota = 1
        for amount in unassigned:
            remaining_payment = amount
            while remaining_payment > 0 and current_quota <= quota_count:
                target = plan_amounts.get(current_quota, Decimal('0.00'))
                available = max(Decimal('0.00'), target - quota_paid[current_quota])
                if available <= 0:
                    current_quota += 1
                    continue
                applied = min(remaining_payment, available)
                quota_paid[current_quota] += applied
                remaining_payment -= applied
                if quota_paid[current_quota] >= target:
                    current_quota += 1
            if remaining_payment > 0 and quota_count:
                quota_paid[quota_count] += remaining_payment

    return quota_paid


def product_quota_payments_report(filters):
    product_id = filters.get('product') or ''
    qs = filter_clients_report(
        community=filters.get('community') or '',
        population_center=filters.get('population_center') or '',
        province=filters.get('province') or '',
        district=filters.get('district') or '',
        location_type=filters.get('location_type') or '',
    )
    client_ids = list(qs.values_list('id', flat=True))
    props = (
        ClientProperty.objects.select_related('client__user', 'product')
        .filter(client_id__in=client_ids, product__isnull=False)
        .order_by('product__name', 'community', 'population_center', 'client__user__last_name')
    )
    if product_id:
        props = props.filter(product_id=product_id)

    prop_ids = [p.id for p in props]
    details = (
        SaleDetail.objects.select_related('sale__client__user', 'product')
        .filter(client_property_id__in=prop_ids, sale__is_voided=False)
        .order_by('-sale_id')
    )
    sale_by_prop = {}
    for detail in details:
        sale_by_prop.setdefault(detail.client_property_id, detail.sale)

    ctas_by_sale = {
        c.sale_id: c
        for c in CtasCollect.objects.select_related('sale')
        .filter(sale_id__in=[s.id for s in sale_by_prop.values()])
    }

    max_quotas = 0
    rows = []
    for prop in props:
        sale = sale_by_prop.get(prop.id)
        cta = ctas_by_sale.get(sale.id) if sale else None
        quota_count = max(1, int(sale.credit_quota_count or 1)) if sale else 0
        max_quotas = max(max_quotas, quota_count)
        initial = Decimal(str(sale.credit_down_payment or 0)).quantize(Decimal('0.01')) if sale else Decimal('0.00')
        quota_paid = _quota_paid_matrix_for_cta(cta) if cta else {}
        paid_total = (
            Decimal(str(cta.debt or 0)) - Decimal(str(cta.saldo or 0))
            if cta else initial
        )
        saldo = Decimal(str(cta.saldo or 0)).quantize(Decimal('0.01')) if cta else Decimal('0.00')
        row = {
            'product': prop.product.name if prop.product_id else '',
            'community': (prop.community or 'Sin comunidad').strip().upper() or 'Sin comunidad',
            'population_center': (prop.population_center or 'Sin centro poblado').strip().upper() or 'Sin centro poblado',
            'client': prop.client.user.get_full_name(),
            'dni': prop.client.user.dni or '',
            'sale_code': sale.sale_code or 'VT-{:06d}'.format(sale.pk) if sale else '',
            'contract_code': sale.contract_code or '' if sale else '',
            'initial': _money(initial),
            'paid_total': _money(paid_total),
            'saldo': _money(saldo),
        }
        for i in range(1, quota_count + 1):
            row['quota_{}'.format(i)] = _money(quota_paid.get(i, Decimal('0.00')))
        rows.append(row)

    columns = [
        {'data': 'product', 'title': 'Producto'},
        {'data': 'community', 'title': 'Comunidad'},
        {'data': 'population_center', 'title': 'Centro poblado'},
        {'data': 'client', 'title': 'Cliente'},
        {'data': 'dni', 'title': 'DNI'},
        {'data': 'sale_code', 'title': 'Venta'},
        {'data': 'contract_code', 'title': 'Contrato'},
        {'data': 'initial', 'title': 'Inicial'},
    ]
    for i in range(1, max_quotas + 1):
        columns.append({'data': 'quota_{}'.format(i), 'title': 'Cuota {}'.format(i)})
    columns.extend([
        {'data': 'paid_total', 'title': 'Total pagado'},
        {'data': 'saldo', 'title': 'Debe'},
    ])
    return {'columns': columns, 'rows': rows}
