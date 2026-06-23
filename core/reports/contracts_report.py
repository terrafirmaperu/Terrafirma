# -*- coding: utf-8 -*-
"""Reporte Contratos: clientes con predio y producto vinculados."""

from core.pos.models import ClientProperty, Product


def _distinct_sorted(values):
    seen = set()
    out = []
    for value in values:
        if not value:
            continue
        key = value.strip().lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(value.strip())
    return sorted(out, key=lambda x: x.lower())


def get_contracts_report_filter_options():
    props = ClientProperty.objects.filter(product__isnull=False)
    products = [
        {'id': p.id, 'name': p.name}
        for p in Product.objects.filter(client_properties__isnull=False)
        .distinct()
        .order_by('name')
    ]
    return {
        'products': products,
        'departments': _distinct_sorted(
            props.exclude(department='').values_list('department', flat=True)
        ),
        'provinces': _distinct_sorted(
            props.exclude(province='').values_list('province', flat=True)
        ),
        'districts': _distinct_sorted(
            props.exclude(district='').values_list('district', flat=True)
        ),
        'communities': _distinct_sorted(
            props.filter(community_location_enabled=True)
            .exclude(community='')
            .values_list('community', flat=True)
        ),
        'population_centers': _distinct_sorted(
            props.filter(community_location_enabled=True)
            .exclude(population_center='')
            .values_list('population_center', flat=True)
        ),
        'predio_types': [
            {'id': choice[0], 'name': choice[1]}
            for choice in ClientProperty._meta.get_field('predio_type').choices
            if choice[0]
        ],
    }


def _filter_label_map(options):
    products = {str(p['id']): p['name'] for p in options.get('products', [])}
    predio_types = {t['id']: t['name'] for t in options.get('predio_types', [])}
    return products, predio_types


def _location_filters_enabled(filters):
    return (filters.get('location_filters_enabled') or '').strip() in ('1', 'true', 'on', 'yes')


def build_contracts_filter_summary(filters, options=None):
    options = options or get_contracts_report_filter_options()
    products, predio_types = _filter_label_map(options)
    parts = []

    product_id = (filters.get('product') or '').strip()
    if product_id:
        parts.append('Producto: {}'.format(products.get(product_id, product_id)))

    location_type = (filters.get('location_type') or '').strip()
    if location_type == 'community':
        parts.append('Ubicación: con comunidad')
    elif location_type == 'population_center':
        parts.append('Ubicación: con centro poblado')

    if _location_filters_enabled(filters):
        department = (filters.get('department') or '').strip()
        if department:
            parts.append('Departamento del predio: {}'.format(department))

        province = (filters.get('province') or '').strip()
        if province:
            parts.append('Provincia del predio: {}'.format(province))

        district = (filters.get('district') or '').strip()
        if district:
            parts.append('Distrito del predio: {}'.format(district))

        community = (filters.get('community') or '').strip()
        if community:
            parts.append('Comunidad: {}'.format(community))

        population_center = (filters.get('population_center') or '').strip()
        if population_center:
            parts.append('Centro poblado: {}'.format(population_center))

    predio_type = (filters.get('predio_type') or '').strip()
    if predio_type:
        parts.append('Tipo de predio: {}'.format(predio_types.get(predio_type, predio_type)))

    if not parts:
        return 'Todos los clientes con predio y producto vinculado'
    return ' · '.join(parts)


def filter_contract_properties(filters):
    qs = ClientProperty.objects.select_related(
        'client__user',
        'product',
    ).filter(product__isnull=False)

    product_id = (filters.get('product') or '').strip()
    if product_id:
        qs = qs.filter(product_id=int(product_id))

    if _location_filters_enabled(filters):
        department = (filters.get('department') or '').strip()
        if department:
            qs = qs.filter(department__iexact=department)

        province = (filters.get('province') or '').strip()
        if province:
            qs = qs.filter(province__iexact=province)

        district = (filters.get('district') or '').strip()
        if district:
            qs = qs.filter(district__iexact=district)

        community = (filters.get('community') or '').strip()
        if community:
            qs = qs.filter(community__iexact=community)

        population_center = (filters.get('population_center') or '').strip()
        if population_center:
            qs = qs.filter(population_center__iexact=population_center)

    predio_type = (filters.get('predio_type') or '').strip()
    if predio_type:
        qs = qs.filter(predio_type=predio_type)

    location_type = (filters.get('location_type') or '').strip()
    if location_type == 'community':
        qs = qs.filter(community_location_enabled=True).exclude(community='')
    elif location_type == 'population_center':
        qs = qs.filter(community_location_enabled=True).exclude(population_center='')

    return qs.order_by(
        'client__user__last_name',
        'client__user__first_name',
        'id',
    )


def property_to_contract_row(prop):
    client = prop.client
    user = client.user
    return {
        'first_name': user.first_name or '',
        'last_name': user.last_name or '',
        'marital_status': (
            client.get_marital_status_display() if client.marital_status else '—'
        ),
        'mobile': client.mobile or '',
        'dni': user.dni or '',
        'product': prop.product.name if prop.product_id else '',
        'predio': prop.__str__(),
    }


def search_contracts_report(filters):
    options = get_contracts_report_filter_options()
    props = filter_contract_properties(filters)
    rows = [property_to_contract_row(prop) for prop in props]
    return {
        'filter_summary': build_contracts_filter_summary(filters, options),
        'rows': rows,
        'total': len(rows),
    }
