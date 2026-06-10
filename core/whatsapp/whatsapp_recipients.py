import json

from django.db.models import Exists, F, OuterRef, Q

from core.pos.models import (
    AdvisoryProgressCase,
    Client,
    ClientProperty,
    CtasCollect,
    PaymentsCtaCollect,
    Sale,
)
from core.reports.client_report import (
    _distinct_sorted,
    filter_clients_report,
    get_client_report_filter_options,
)
from core.whatsapp.whatsapp_api import normalize_phone_pe

AUDIENCE_ALL = 'all'
AUDIENCE_DEBTORS = 'debtors'
AUDIENCE_PAYERS = 'payers'
AUDIENCE_PROCESS_DONE = 'process_completed'

AUDIENCE_CHOICES = (
    (AUDIENCE_ALL, 'Todos los clientes del filtro'),
    (AUDIENCE_DEBTORS, 'Clientes con deuda pendiente'),
    (AUDIENCE_PAYERS, 'Clientes que ya pagaron (cuotas o contado)'),
    (AUDIENCE_PROCESS_DONE, 'Procesos de asesoría completados'),
)

LOCATION_BASE_PREDIO = 'predio'
LOCATION_BASE_CLIENT = 'client'

LOCATION_BASE_CHOICES = (
    (LOCATION_BASE_PREDIO, 'Ubicación del predio vinculado'),
    (LOCATION_BASE_CLIENT, 'Ubicación del cliente (domicilio)'),
)


def parse_filter_criteria(raw):
    if not raw:
        return {}
    if isinstance(raw, dict):
        return raw
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}


def get_whatsapp_filter_options():
    """Opciones de filtro para mensajería (domicilio cliente vs predio vinculado)."""
    base = get_client_report_filter_options()
    prop_qs = ClientProperty.objects.all()
    base['client_departments'] = _distinct_sorted(
        Client.objects.exclude(department='').values_list('department', flat=True)
    )
    base['client_provinces'] = _distinct_sorted(
        Client.objects.exclude(province='').values_list('province', flat=True)
    )
    base['client_districts'] = _distinct_sorted(
        Client.objects.exclude(district='').values_list('district', flat=True)
    )
    base['predio_provinces'] = _distinct_sorted(
        list(prop_qs.exclude(province='').values_list('province', flat=True))
        + list(Client.objects.filter(has_predio=True).exclude(predio_province='').values_list('predio_province', flat=True))
    )
    base['predio_districts'] = _distinct_sorted(
        list(prop_qs.exclude(district='').values_list('district', flat=True))
        + list(Client.objects.filter(has_predio=True).exclude(predio_district='').values_list('predio_district', flat=True))
    )
    base['predio_departments'] = _distinct_sorted(
        list(prop_qs.exclude(department='').values_list('department', flat=True))
        + list(Client.objects.filter(has_predio=True).exclude(predio_department='').values_list('predio_department', flat=True))
    )
    return base


def build_filter_criteria_from_post(post):
    product = (post.get('filter_product') or '').strip()
    location_base = (post.get('filter_location_base') or LOCATION_BASE_PREDIO).strip()
    if location_base not in (LOCATION_BASE_PREDIO, LOCATION_BASE_CLIENT):
        location_base = LOCATION_BASE_PREDIO
    if location_base == LOCATION_BASE_CLIENT:
        province = (post.get('filter_client_province') or '').strip()
        district = (post.get('filter_client_district') or '').strip()
        department = (post.get('filter_department') or '').strip()
        client_address = (post.get('filter_client_address') or '').strip()
        community = ''
        population_center = ''
        predio_address = ''
    else:
        province = (post.get('filter_province') or '').strip()
        district = (post.get('filter_district') or '').strip()
        department = (post.get('filter_predio_department') or '').strip()
        predio_address = (post.get('filter_predio_address') or '').strip()
        community = (post.get('filter_community') or '').strip()
        population_center = (post.get('filter_population_center') or '').strip()
        client_address = ''
    return {
        'audience': (post.get('filter_audience') or AUDIENCE_ALL).strip(),
        'location_base': location_base,
        'community': community,
        'population_center': population_center,
        'province': province,
        'district': district,
        'department': department,
        'predio_address': predio_address,
        'client_address': client_address,
        'location_type': (post.get('filter_location_type') or '').strip(),
        'product_id': int(product) if product.isdigit() else '',
    }


def filter_criteria_label(criteria):
    criteria = parse_filter_criteria(criteria)
    if not criteria:
        return 'Sin filtros'
    parts = []
    audience = criteria.get('audience') or AUDIENCE_ALL
    for key, label in AUDIENCE_CHOICES:
        if key == audience:
            parts.append(label)
            break
    location_base = criteria.get('location_base') or LOCATION_BASE_PREDIO
    for key, label in LOCATION_BASE_CHOICES:
        if key == location_base:
            parts.append(label)
            break
    for field, title in (
        ('department', 'Departamento'),
        ('community', 'Comunidad'),
        ('population_center', 'Centro poblado'),
        ('province', 'Provincia'),
        ('district', 'Distrito'),
    ):
        if criteria.get(field):
            parts.append('{}: {}'.format(title, criteria[field]))
    if criteria.get('predio_address'):
        parts.append('Dirección predio: {}'.format(criteria['predio_address']))
    if criteria.get('client_address'):
        parts.append('Dirección cliente: {}'.format(criteria['client_address']))
    if criteria.get('product_id'):
        parts.append('Producto ID: {}'.format(criteria['product_id']))
    return ' · '.join(parts) if parts else 'Filtro de clientes'


def queryset_filtered_clients(criteria):
    criteria = parse_filter_criteria(criteria)
    qs = filter_clients_report(
        community=criteria.get('community') or '',
        population_center=criteria.get('population_center') or '',
        province=criteria.get('province') or '',
        district=criteria.get('district') or '',
        location_type=criteria.get('location_type') or '',
        location_base=criteria.get('location_base') or LOCATION_BASE_PREDIO,
        department=criteria.get('department') or '',
        predio_address=criteria.get('predio_address') or '',
        client_address=criteria.get('client_address') or '',
    )

    product_id = criteria.get('product_id') or ''
    if product_id:
        qs = qs.filter(properties__product_id=product_id).distinct()

    audience = criteria.get('audience') or AUDIENCE_ALL
    if audience == AUDIENCE_DEBTORS:
        qs = qs.filter(
            Exists(
                CtasCollect.objects.filter(
                    sale__client_id=OuterRef('pk'),
                    state=True,
                    saldo__gt=0,
                    sale__is_voided=False,
                )
            )
        )
    elif audience == AUDIENCE_PAYERS:
        qs = qs.filter(
            Q(
                Exists(
                    PaymentsCtaCollect.objects.filter(
                        ctascollect__sale__client_id=OuterRef('pk'),
                    )
                )
            )
            | Q(
                Exists(
                    Sale.objects.filter(
                        client_id=OuterRef('pk'),
                        is_voided=False,
                    ).filter(
                        Q(payment_condition='contado')
                        | Q(credit_down_payment__gt=0)
                    )
                )
            )
        )
    elif audience == AUDIENCE_PROCESS_DONE:
        qs = qs.filter(
            Exists(
                AdvisoryProgressCase.objects.filter(
                    client_id=OuterRef('pk'),
                    current_stage__gte=F('total_stages'),
                )
            )
        )

    return qs.distinct()


def phones_from_clients(qs):
    phones = []
    seen = set()
    for mobile in qs.exclude(mobile='').values_list('mobile', flat=True):
        normalized = normalize_phone_pe(mobile)
        if normalized and normalized not in seen:
            seen.add(normalized)
            phones.append(normalized)
    return phones


def get_phones_for_campaign(campaign):
    from core.whatsapp.models import WhatsAppBulkMessage

    if campaign.recipient_source == WhatsAppBulkMessage.SOURCE_MANUAL:
        from core.whatsapp.whatsapp_api import parse_recipients_text
        return parse_recipients_text(campaign.recipients_text)

    if campaign.recipient_source == WhatsAppBulkMessage.SOURCE_FILTER:
        qs = queryset_filtered_clients(campaign.filter_criteria)
        return phones_from_clients(qs)

    if campaign.recipient_source == WhatsAppBulkMessage.SOURCE_CLIENTS:
        from core.whatsapp.whatsapp_api import get_client_phones
        return get_client_phones()

    return []


def count_phones_for_post(post):
    from core.whatsapp.models import WhatsAppBulkMessage

    source = post.get('recipient_source', WhatsAppBulkMessage.SOURCE_MANUAL)
    if source == WhatsAppBulkMessage.SOURCE_MANUAL:
        from core.whatsapp.whatsapp_api import parse_recipients_text
        return len(parse_recipients_text(post.get('recipients_text', '')))
    if source == WhatsAppBulkMessage.SOURCE_CLIENTS:
        from core.whatsapp.whatsapp_api import get_client_phones
        return len(get_client_phones())
    if source == WhatsAppBulkMessage.SOURCE_FILTER:
        criteria = build_filter_criteria_from_post(post)
        return len(phones_from_clients(queryset_filtered_clients(criteria)))
    return 0
