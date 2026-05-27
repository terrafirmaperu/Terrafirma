# -*- coding: utf-8 -*-
"""Consultas y serialización para el reporte de clientes."""

from django.db.models import Prefetch, Q

from core.pos.models import AdvisoryProgressCase, Client, ClientProperty, Sale


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
    return {
        'communities': communities,
        'population_centers': population_centers,
        'provinces': provinces,
        'districts': districts,
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
