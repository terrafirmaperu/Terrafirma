"""Casos de asesoría vinculados a ventas / contratas."""

from core.pos.client_properties import client_property_to_dict, property_summary_line


def _sale_product_ids(sale):
    return set(
        sale.saledetail_set.values_list('product_id', flat=True)
    )


def build_sale_products_line(sale):
    names = []
    for detail in sale.saledetail_set.select_related('product').order_by('id'):
        name = (detail.product.name or '').strip()
        if name:
            if detail.cant and detail.cant != 1:
                names.append('{} (×{})'.format(name, detail.cant))
            else:
                names.append(name)
    return ', '.join(names)[:500]


def build_sale_predio_summary_from_sale(sale):
    if not sale.client_id:
        return ''
    lines = []
    seen_prop = set()
    for detail in sale.saledetail_set.select_related('client_property').order_by('id'):
        prop = detail.client_property
        if prop and prop.pk not in seen_prop:
            seen_prop.add(prop.pk)
            line = property_summary_line(client_property_to_dict(prop))
            if line:
                lines.append(line)
    if lines:
        return ' | '.join(lines)[:500]
    product_ids = _sale_product_ids(sale)
    if product_ids:
        props = sale.client.properties.filter(product_id__in=product_ids).order_by('order', 'id')
        for prop in props:
            line = property_summary_line(client_property_to_dict(prop))
            if line:
                lines.append(line)
    if not lines and product_ids:
        props = sale.client.properties.order_by('order', 'id')[:3]
        for prop in props:
            line = property_summary_line(client_property_to_dict(prop))
            if line:
                lines.append(line)
    return ' | '.join(lines)[:500]


def build_sale_case_title(sale):
    cc = sale.contract_code or ('CT-{:06d}'.format(sale.id) if sale.id else 'Contrato')
    details = list(sale.saledetail_set.select_related('product').order_by('id')[:3])
    if len(details) == 1:
        name = (details[0].product.name or '').strip()
        if name:
            return '{} — {}'.format(name, cc)
    if details:
        names = ', '.join(
            (d.product.name or '').strip() for d in details if (d.product.name or '').strip()
        )
        if names:
            return '{} — {}'.format(names[:120], cc)
    return 'Contrato {}'.format(cc)


def sale_advisory_json(sale):
    if not sale:
        return None
    details = []
    for row in sale.saledetail_set.select_related('product').order_by('id'):
        details.append({
            'product_name': row.product.name,
            'cant': row.cant,
            'total': format(row.total, '.2f'),
        })
    products_line = build_sale_products_line(sale)
    return {
        'id': sale.id,
        'sale_code': sale.sale_code or '',
        'contract_code': sale.contract_code or '',
        'date_joined': sale.date_joined.strftime('%Y-%m-%d'),
        'date_joined_display': sale.date_joined.strftime('%d/%m/%Y'),
        'total': format(sale.total, '.2f'),
        'payment_condition': sale.payment_condition,
        'payment_condition_label': sale.get_payment_condition_display(),
        'products_summary': products_line,
        'details': details,
    }


def ensure_advisory_case_for_sale(sale):
    """Crea o devuelve el caso de asesoría asociado a una venta (contrata)."""
    if not sale or not sale.client_id:
        return None

    from core.pos.models import AdvisoryProgressCase

    from core.pos.models import sync_advisory_progress_stages

    existing = AdvisoryProgressCase.objects.filter(sale_id=sale.pk).first()
    if existing:
        if existing.stages.count() == 0:
            sync_advisory_progress_stages(existing)
        return existing

    sale = type(sale).objects.select_related('client').prefetch_related(
        'saledetail_set__product',
        'client__properties__product',
    ).get(pk=sale.pk)

    title = build_sale_case_title(sale)
    predio_summary = build_sale_predio_summary_from_sale(sale)
    if not predio_summary:
        predio_summary = build_sale_products_line(sale)

    case = AdvisoryProgressCase.objects.create(
        client_id=sale.client_id,
        sale=sale,
        title=title,
        predio_summary=predio_summary,
        total_stages=5,
        current_stage=1,
        is_visible_portal=True,
    )
    if case.stages.count() == 0:
        sync_advisory_progress_stages(case)
    return case


def sync_advisory_cases_for_client(client):
    """Crea casos de asesoría para cada venta del cliente que ya tiene código de contrato."""
    if not client or not getattr(client, 'pk', None):
        return 0

    from core.pos.models import AdvisoryProgressCase, Sale

    sale_ids = list(
        Sale.objects.filter(client_id=client.pk, is_voided=False)
        .exclude(contract_code__isnull=True)
        .exclude(contract_code='')
        .order_by('-id')
        .values_list('pk', flat=True)
    )
    if not sale_ids:
        return 0

    linked_sale_ids = set(
        AdvisoryProgressCase.objects.filter(
            client_id=client.pk,
            sale_id__in=sale_ids,
        ).values_list('sale_id', flat=True)
    )
    created = 0
    for sale in Sale.objects.filter(pk__in=sale_ids).prefetch_related(
        'saledetail_set__product',
        'client__properties__product',
    ).order_by('-id'):
        if sale.pk in linked_sale_ids:
            continue
        if ensure_advisory_case_for_sale(sale):
            created += 1
    return created
