import json

from django.db.models import Exists, F, OuterRef, Q

from core.pos.models import AdvisoryProgressCase, Client, CtasCollect, PaymentsCtaCollect, Sale
from core.reports.client_report import filter_clients_report, get_client_report_filter_options
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


def build_filter_criteria_from_post(post):
    product = (post.get('filter_product') or '').strip()
    return {
        'audience': (post.get('filter_audience') or AUDIENCE_ALL).strip(),
        'community': (post.get('filter_community') or '').strip(),
        'population_center': (post.get('filter_population_center') or '').strip(),
        'province': (post.get('filter_province') or '').strip(),
        'district': (post.get('filter_district') or '').strip(),
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
    for field, title in (
        ('community', 'Comunidad'),
        ('population_center', 'Centro poblado'),
        ('province', 'Provincia'),
        ('district', 'Distrito'),
    ):
        if criteria.get(field):
            parts.append('{}: {}'.format(title, criteria[field]))
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
