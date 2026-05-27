import json
from decimal import Decimal, InvalidOperation

from core.pos.models import Client, ClientProperty


def _decimal_or_none(value):
    if value is None or value == '':
        return None
    try:
        return Decimal(str(value).replace(',', '.'))
    except (InvalidOperation, ValueError):
        return None


def _property_has_content(fields):
    keys = (
        'department', 'province', 'district', 'address',
        'lot_number', 'block', 'registry_number', 'label',
    )
    for key in keys:
        if (fields.get(key) or '').strip():
            return True
    if fields.get('area') is not None or fields.get('perimeter') is not None:
        return True
    if (fields.get('predio_type') or '').strip():
        return True
    if fields.get('community_location_enabled'):
        if (fields.get('community') or '').strip() or (fields.get('population_center') or '').strip():
            return True
    return False


def _bool_from_json(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ('1', 'true', 'on', 'yes')
    return bool(value)


def _parse_product_id(item):
    raw = item.get('product_id')
    if raw in (None, '', 0, '0'):
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _property_fields_from_dict(item):
    community_enabled = _bool_from_json(item.get('community_location_enabled'))
    return {
        'label': (item.get('label') or '').strip()[:120],
        'department': (item.get('department') or '').strip()[:80],
        'province': (item.get('province') or '').strip()[:80],
        'district': (item.get('district') or '').strip()[:80],
        'community_location_enabled': community_enabled,
        'community': (item.get('community') or '').strip()[:120] if community_enabled else '',
        'population_center': (item.get('population_center') or '').strip()[:200] if community_enabled else '',
        'address': (item.get('address') or '').strip()[:500],
        'lot_number': (item.get('lot_number') or '').strip()[:30],
        'block': (item.get('block') or '').strip()[:30],
        'registry_number': (item.get('registry_number') or '').strip()[:50],
        'predio_type': (item.get('predio_type') or '').strip()[:30] or None,
        'area': _decimal_or_none(item.get('area')),
        'perimeter': _decimal_or_none(item.get('perimeter')),
    }


def legacy_client_to_property_dict(client):
    return {
        'id': None,
        'label': '',
        'department': client.predio_department or '',
        'province': client.predio_province or '',
        'district': client.predio_district or '',
        'address': client.predio_address or '',
        'lot_number': client.predio_lot_number or '',
        'block': client.predio_block or '',
        'registry_number': client.predio_registry_number or '',
        'predio_type': client.predio_type or '',
        'area': '' if client.predio_area is None else format(client.predio_area, '.2f'),
        'perimeter': '' if client.predio_perimeter is None else format(client.predio_perimeter, '.2f'),
        'is_primary': True,
    }


def _empty_predio_process():
    return {
        'in_process': False,
        'process_label': '',
        'contract_code': '',
        'sale_code': '',
        'block_message': '',
        'has_advisory': False,
    }


def find_existing_sale_for_predio_property(prop):
    """Venta activa vinculada a este predio (no a otro del mismo cliente/producto)."""
    if not prop or not prop.client_id:
        return None
    from core.pos.models import Sale

    if prop.id:
        sale = (
            Sale.objects.filter(
                client_id=prop.client_id,
                is_voided=False,
                saledetail__client_property_id=prop.id,
            )
            .distinct()
            .order_by('-id')
            .first()
        )
        if sale:
            return sale

    if not prop.product_id:
        return None

    legacy = (
        Sale.objects.filter(
            client_id=prop.client_id,
            is_voided=False,
            saledetail__product_id=prop.product_id,
            saledetail__client_property__isnull=True,
        )
        .distinct()
        .order_by('-id')
    )
    if not legacy.exists():
        return None

    siblings = ClientProperty.objects.filter(
        client_id=prop.client_id,
        product_id=prop.product_id,
    ).order_by('order', 'id')
    if siblings.count() <= 1:
        return legacy.first()

    locked = siblings.filter(contract_locked_at__isnull=False).order_by('contract_locked_at', 'id')
    if locked.count() == 1 and locked.first().pk == prop.pk:
        return legacy.first()

    if locked.exists():
        return None

    oldest = siblings.first()
    if oldest and oldest.pk == prop.pk:
        return legacy.first()
    return None


def find_existing_sale_for_predio_product(client_id, product_id):
    """Compatibilidad: solo si hay un único predio con ese producto."""
    if not client_id or not product_id:
        return None
    props = ClientProperty.objects.filter(client_id=client_id, product_id=product_id)
    if props.count() == 1:
        return find_existing_sale_for_predio_property(props.first())
    return None


def _product_payload_entries(products_payload):
    for item in products_payload or []:
        if isinstance(item, dict):
            yield item
        else:
            yield {'id': item}


def find_duplicate_predio_sales(client_id, products_payload):
    """Ventas ya registradas para el predio concreto (o producto único legacy)."""
    if not client_id:
        return []
    from core.pos.models import AdvisoryProgressCase

    duplicates = []
    seen_props = set()
    seen_prod_only = set()

    for item in _product_payload_entries(products_payload):
        try:
            product_id = int(item.get('id'))
        except (TypeError, ValueError):
            continue
        raw_prop = item.get('client_property_id')
        prop_id = None
        if raw_prop not in (None, '', 0, '0'):
            try:
                prop_id = int(raw_prop)
            except (TypeError, ValueError):
                prop_id = None

        if prop_id:
            if prop_id in seen_props:
                continue
            seen_props.add(prop_id)
            prop = ClientProperty.objects.filter(pk=prop_id, client_id=client_id).first()
            if not prop:
                continue
            sale = find_existing_sale_for_predio_property(prop)
            label = (prop.label or '').strip() or property_summary_line(client_property_to_dict(prop))
        else:
            if product_id in seen_prod_only:
                continue
            seen_prod_only.add(product_id)
            props = ClientProperty.objects.filter(client_id=client_id, product_id=product_id)
            if props.count() != 1:
                continue
            prop = props.first()
            sale = find_existing_sale_for_predio_property(prop)
            label = (prop.label or '').strip() or property_summary_line(client_property_to_dict(prop))

        if not sale:
            continue
        case = AdvisoryProgressCase.objects.filter(sale_id=sale.pk).first()
        duplicates.append({
            'product_id': product_id,
            'client_property_id': prop.id if prop else None,
            'property_label': label,
            'sale_id': sale.id,
            'sale_code': sale.sale_code or '',
            'contract_code': sale.contract_code or '',
            'has_advisory': case is not None,
        })
    return duplicates


def format_duplicate_predio_sale_error(duplicates):
    if not duplicates:
        return ''
    lines = []
    for item in duplicates:
        title = item.get('property_label') or 'Predio / servicio'
        refs = []
        if item.get('sale_code'):
            refs.append('venta {}'.format(item['sale_code']))
        if item.get('contract_code'):
            refs.append('contrato {}'.format(item['contract_code']))
        ref_txt = ' ({})'.format(', '.join(refs)) if refs else ''
        lines.append(
            '«{title}» ya tiene una venta registrada{refs}. '
            'No puede generar la misma asesoría otra vez: ya está generada en el sistema.'.format(
                title=title,
                refs=ref_txt,
            )
        )
    return '\n'.join(lines)


def validate_sale_products_not_duplicated(client_id, products_payload):
    duplicates = find_duplicate_predio_sales(client_id, products_payload)
    return format_duplicate_predio_sale_error(duplicates)


def predio_sale_process_info(prop):
    """Estado de venta/asesoría existente para un predio (facturación)."""
    if not prop or not prop.client_id:
        return _empty_predio_process()

    from core.pos.models import AdvisoryProgressCase

    sale = None
    case = None
    sale = find_existing_sale_for_predio_property(prop)
    if sale:
        case = AdvisoryProgressCase.objects.filter(sale_id=sale.pk).first()

    if sale:
        contract_code = sale.contract_code or ''
        sale_code = sale.sale_code or ''
        label = 'Ya generado en el sistema'
        if contract_code:
            label = 'Ya generado — {}'.format(contract_code)
        elif sale_code:
            label = 'Ya generado — {}'.format(sale_code)
        block_message = (
            'Este predio ya tiene una venta registrada en el sistema. '
            'No puede generar la misma asesoría otra vez.'
        )
        if sale_code:
            block_message += ' Venta: {}.'.format(sale_code)
        if contract_code:
            block_message += ' Contrato: {}.'.format(contract_code)
        if case:
            block_message += ' La asesoría ya está activa.'
        return {
            'in_process': True,
            'process_label': label,
            'contract_code': contract_code,
            'sale_code': sale_code,
            'block_message': block_message,
            'has_advisory': case is not None,
        }

    if getattr(prop, 'contract_locked_at', None) and prop.product_id:
        locked_sale = find_existing_sale_for_predio_property(prop)
        case = (
            AdvisoryProgressCase.objects.filter(sale_id=locked_sale.pk).first()
            if locked_sale
            else None
        )
        if case and case.sale_id:
            sale = case.sale
            contract_code = sale.contract_code or ''
            sale_code = sale.sale_code or ''
            label = 'Ya en proceso'
            if contract_code:
                label = 'Ya en proceso — {}'.format(contract_code)
            return {
                'in_process': True,
                'process_label': label,
                'contract_code': contract_code,
                'sale_code': sale_code,
                'block_message': (
                    'Este predio ya tiene contrata generada. '
                    'No puede repetir la misma venta ni la misma asesoría.'
                ),
                'has_advisory': True,
            }

    return _empty_predio_process()


def client_property_to_dict(prop):
    from core.pos.product_sale import product_json_for_sale_row

    process = predio_sale_process_info(prop)
    item = {
        'id': prop.id,
        'label': prop.label or '',
        'department': prop.department or '',
        'province': prop.province or '',
        'district': prop.district or '',
        'community_location_enabled': bool(prop.community_location_enabled),
        'community': prop.community or '',
        'population_center': prop.population_center or '',
        'address': prop.address or '',
        'lot_number': prop.lot_number or '',
        'block': prop.block or '',
        'registry_number': prop.registry_number or '',
        'predio_type': prop.predio_type or '',
        'predio_type_display': prop.get_predio_type_display() if prop.predio_type else '',
        'area': '' if prop.area is None else format(prop.area, '.2f'),
        'perimeter': '' if prop.perimeter is None else format(prop.perimeter, '.2f'),
        'is_primary': bool(prop.is_primary),
        'contract_locked': prop.contract_locked_at is not None,
        'in_process': process['in_process'],
        'process_label': process['process_label'],
        'linked_contract_code': process['contract_code'],
        'linked_sale_code': process['sale_code'],
        'block_message': process.get('block_message') or '',
        'has_advisory': bool(process.get('has_advisory')),
        'product_id': prop.product_id or '',
        'product_name': '',
        'product_price': '',
        'product_sale': None,
    }
    if prop.product_id and getattr(prop, 'product', None):
        item['product_name'] = prop.product.name
        item['product_price'] = format(prop.product.get_price_current(), '.2f')
        ps = product_json_for_sale_row(prop.product)
        ps['client_property_id'] = prop.id
        item['product_sale'] = ps
    return item


def load_properties_for_client(client):
    if not client or not getattr(client, 'pk', None):
        return []
    props = list(
        client.properties.select_related('product', 'product__category').order_by('order', 'id')
    )
    if props:
        return [client_property_to_dict(p) for p in props]
    if client.has_predio:
        return [legacy_client_to_property_dict(client)]
    return []


def property_summary_line(prop_dict):
    parts = []
    label = (prop_dict.get('label') or '').strip()
    if label:
        parts.append(label)
    lot = (prop_dict.get('lot_number') or '').strip()
    block = (prop_dict.get('block') or '').strip()
    if lot:
        parts.append('Lote {}'.format(lot))
    if block:
        parts.append('Mz. {}'.format(block))
    loc = ' — '.join(
        p for p in [
            prop_dict.get('district') or '',
            prop_dict.get('province') or '',
            prop_dict.get('department') or '',
        ] if p
    )
    if loc:
        parts.append(loc)
    if prop_dict.get('community_location_enabled'):
        comunidad = (prop_dict.get('community') or '').strip()
        centro = (prop_dict.get('population_center') or '').strip()
        if comunidad:
            parts.append('Com. {}'.format(comunidad))
        if centro:
            parts.append('C.P. {}'.format(centro))
    addr = (prop_dict.get('address') or '').strip()
    if addr and not loc:
        parts.append(addr)
    return ', '.join(parts)


def sync_client_legacy_predio(client):
    primary = (
        client.properties.filter(is_primary=True).order_by('order', 'id').first()
        or client.properties.order_by('order', 'id').first()
    )
    if not primary:
        client.has_predio = False
        client.predio_department = ''
        client.predio_province = ''
        client.predio_district = ''
        client.predio_address = ''
        client.predio_area = None
        client.predio_perimeter = None
        client.predio_lot_number = ''
        client.predio_block = ''
        client.predio_registry_number = ''
        client.predio_type = None
        client.save(update_fields=[
            'has_predio', 'predio_department', 'predio_province', 'predio_district',
            'predio_address', 'predio_area', 'predio_perimeter', 'predio_lot_number',
            'predio_block', 'predio_registry_number', 'predio_type',
        ])
        return

    client.has_predio = True
    client.predio_department = primary.department or ''
    client.predio_province = primary.province or ''
    client.predio_district = primary.district or ''
    if primary.community_location_enabled and primary.population_center:
        client.predio_address = primary.population_center
    elif primary.community_location_enabled and primary.community:
        client.predio_address = primary.community
    else:
        client.predio_address = primary.address or ''
    client.predio_area = primary.area
    client.predio_perimeter = primary.perimeter
    client.predio_lot_number = primary.lot_number or ''
    client.predio_block = primary.block or ''
    client.predio_registry_number = primary.registry_number or ''
    client.predio_type = primary.predio_type
    client.save(update_fields=[
        'has_predio', 'predio_department', 'predio_province', 'predio_district',
        'predio_address', 'predio_area', 'predio_perimeter', 'predio_lot_number',
        'predio_block', 'predio_registry_number', 'predio_type',
    ])


def client_predios_template_context(instance=None):
    from core.pos.forms import ClientForm
    from core.pos.product_sale import products_catalog_for_predio

    return {
        'client_properties': load_properties_for_client(instance) if instance else [],
        'predio_type_choices': [
            {'id': value, 'name': label}
            for value, label in Client.PREDIO_TYPE_CHOICES
        ],
        'peru_departments': [
            {'id': value, 'name': label}
            for value, label in ClientForm.PERU_DEPARTMENTS if value
        ],
        'predio_products_catalog': products_catalog_for_predio(),
    }


def _sale_product_ids_for_lock(sale):
    from core.pos.models import SaleDetail

    return list(
        SaleDetail.objects.filter(sale_id=sale.pk)
        .values_list('product_id', flat=True)
        .distinct()
    )


def lock_client_properties_for_sale_contract(sale):
    """Bloquea solo el predio vinculado en cada línea de venta (no todos con el mismo producto)."""
    if not sale or not sale.client_id:
        return 0
    from django.utils import timezone
    from core.pos.models import SaleDetail

    prop_ids = list(
        SaleDetail.objects.filter(sale_id=sale.pk, client_property_id__isnull=False)
        .values_list('client_property_id', flat=True)
        .distinct()
    )
    if not prop_ids:
        product_ids = [pid for pid in _sale_product_ids_for_lock(sale) if pid]
        if not product_ids:
            from core.pos.advisory_sale_cases import ensure_advisory_case_for_sale

            ensure_advisory_case_for_sale(sale)
            return 0
        for pid in product_ids:
            props = ClientProperty.objects.filter(
                client_id=sale.client_id,
                product_id=pid,
            )
            if props.count() == 1:
                prop_ids.append(props.first().pk)

    locked = 0
    if prop_ids:
        locked = ClientProperty.objects.filter(
            pk__in=prop_ids,
            contract_locked_at__isnull=True,
        ).update(contract_locked_at=timezone.now())

    from core.pos.advisory_sale_cases import ensure_advisory_case_for_sale

    ensure_advisory_case_for_sale(sale)
    return locked


def unlock_client_properties_for_sale(sale):
    """Quita el bloqueo de los predios vinculados en el detalle de la venta anulada."""
    if not sale or not sale.client_id:
        return 0
    from core.pos.models import SaleDetail

    prop_ids = list(
        SaleDetail.objects.filter(sale_id=sale.pk, client_property_id__isnull=False)
        .values_list('client_property_id', flat=True)
        .distinct()
    )
    if prop_ids:
        return ClientProperty.objects.filter(pk__in=prop_ids).update(contract_locked_at=None)
    product_ids = [pid for pid in _sale_product_ids_for_lock(sale) if pid]
    if not product_ids:
        return 0
    return ClientProperty.objects.filter(
        client_id=sale.client_id,
        product_id__in=product_ids,
    ).update(contract_locked_at=None)


def repair_client_property_contract_locks(client_id=None):
    """
    Corrige bloqueos erróneos (p. ej. todos los predios bloqueados por una sola contrata).
    Deja bloqueado solo si existe venta activa con contrato para ese producto del predio.
    """
    qs = ClientProperty.objects.filter(contract_locked_at__isnull=False)
    if client_id:
        qs = qs.filter(client_id=client_id)
    fixed = 0
    for prop in qs.iterator():
        if not prop.product_id:
            ClientProperty.objects.filter(pk=prop.pk).update(contract_locked_at=None)
            fixed += 1
            continue
        sale = find_existing_sale_for_predio_property(prop)
        if not sale or not (sale.contract_code or '').strip():
            ClientProperty.objects.filter(pk=prop.pk).update(contract_locked_at=None)
            fixed += 1
    return fixed


def locked_properties_pending_removal(client, kept_ids):
    return ClientProperty.objects.filter(
        client=client,
        contract_locked_at__isnull=False,
    ).exclude(pk__in=kept_ids or [])


def _kept_property_ids_from_items(items):
    kept = []
    for item in items:
        if not isinstance(item, dict):
            continue
        raw_id = item.get('id')
        if raw_id in (None, '', 0, '0'):
            continue
        try:
            kept.append(int(raw_id))
        except (TypeError, ValueError):
            continue
    return kept


def save_client_properties_from_request(request, client, raw_json):
    """Guarda predios; exige supervisor si se desvinculan predios con contrato."""
    try:
        items = json.loads(raw_json) if isinstance(raw_json, str) else (raw_json or [])
    except (json.JSONDecodeError, TypeError):
        items = []
    if not isinstance(items, list):
        items = []

    allow_locked_removal = False
    if client.pk:
        kept_ids = _kept_property_ids_from_items(items)
        if locked_properties_pending_removal(client, kept_ids).exists():
            from core.security.mixins import consume_supervisor_predio_unlock

            allowed, err = consume_supervisor_predio_unlock(request)
            if not allowed:
                raise ValueError(err or (
                    'Hay predios con contrato generado. Un supervisor debe autorizar su desvinculación.'
                ))
            allow_locked_removal = True

    save_client_properties_from_json(client, raw_json, allow_locked_removal=allow_locked_removal)


def save_client_properties_from_json(client, raw_json, allow_locked_removal=False):
    try:
        items = json.loads(raw_json) if isinstance(raw_json, str) else (raw_json or [])
    except (json.JSONDecodeError, TypeError):
        items = []
    if not isinstance(items, list):
        items = []

    kept_ids = []
    order_idx = 0
    for item in items:
        if not isinstance(item, dict):
            continue
        fields = _property_fields_from_dict(item)
        if not _property_has_content(fields):
            continue
        product_id = _parse_product_id(item)
        if not product_id:
            raise ValueError(
                'Cada predio debe tener un producto vinculado para poder facturarlo con precio establecido.'
            )
        raw_id = item.get('id')
        prop = None
        if raw_id not in (None, '', 0, '0'):
            try:
                prop = ClientProperty.objects.get(pk=int(raw_id), client=client)
            except (ClientProperty.DoesNotExist, ValueError, TypeError):
                prop = None
        if prop:
            for key, value in fields.items():
                setattr(prop, key, value)
            prop.product_id = product_id
            prop.order = order_idx
            prop.is_primary = order_idx == 0
            prop.save()
        else:
            prop = ClientProperty.objects.create(
                client=client,
                order=order_idx,
                is_primary=order_idx == 0,
                product_id=product_id,
                **fields,
            )
        kept_ids.append(prop.pk)
        order_idx += 1

    pending_locked = locked_properties_pending_removal(client, kept_ids)
    if pending_locked.exists() and not allow_locked_removal:
        raise ValueError(
            'Hay predios con contrato generado. Un supervisor debe autorizar su desvinculación.'
        )

    ClientProperty.objects.filter(client=client).exclude(pk__in=kept_ids).delete()
    sync_client_legacy_predio(client)
