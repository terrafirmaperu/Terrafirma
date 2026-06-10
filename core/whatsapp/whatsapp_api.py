import json
import re
import urllib.error
import urllib.request

from core.whatsapp.whatsapp_config import get_whatsapp_api_settings


def normalize_phone_pe(raw):
    """Convierte a formato internacional sin + para la API de Meta (ej. 51921047681)."""
    digits = re.sub(r'\D', '', raw or '')
    if not digits:
        return None
    if digits.startswith('51') and len(digits) == 11:
        return digits
    if len(digits) == 9 and digits[0] == '9':
        return '51' + digits
    if len(digits) == 10 and digits.startswith('0'):
        return '51' + digits[1:]
    if 10 <= len(digits) <= 15:
        return digits
    return None


def parse_recipients_text(text):
    phones = []
    seen = set()
    for chunk in re.split(r'[\s,;]+', text or ''):
        normalized = normalize_phone_pe(chunk.strip())
        if normalized and normalized not in seen:
            seen.add(normalized)
            phones.append(normalized)
    return phones


def get_client_phones():
    from core.pos.models import Client

    phones = []
    seen = set()
    for mobile in Client.objects.exclude(mobile__isnull=True).exclude(mobile='').values_list('mobile', flat=True):
        normalized = normalize_phone_pe(mobile)
        if normalized and normalized not in seen:
            seen.add(normalized)
            phones.append(normalized)
    return phones


def _api_request(method, url, token, payload=None, timeout=30):
    headers = {
        'Authorization': 'Bearer {}'.format(token),
        'Content-Type': 'application/json',
    }
    data = json.dumps(payload).encode('utf-8') if payload is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode('utf-8')
            return {'ok': True, 'status': resp.status, 'data': json.loads(body) if body else {}}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode('utf-8', errors='replace')
        try:
            parsed = json.loads(detail)
        except json.JSONDecodeError:
            parsed = {'raw': detail}
        return {'ok': False, 'status': exc.code, 'error': parsed}
    except Exception as exc:
        return {'ok': False, 'status': 0, 'error': str(exc)}


def send_text_message(phone_e164, text, settings=None):
    settings = settings or get_whatsapp_api_settings()
    if not settings or not settings.get('enabled'):
        return {'ok': False, 'error': 'API de WhatsApp no configurada o deshabilitada.'}

    to_number = normalize_phone_pe(phone_e164)
    if not to_number:
        return {'ok': False, 'error': 'Número de teléfono inválido: {}'.format(phone_e164)}

    payload = {
        'messaging_product': 'whatsapp',
        'to': to_number,
        'type': 'text',
        'text': {'body': text},
    }
    result = _api_request(
        'POST',
        settings['messages_endpoint'],
        settings['api_token'],
        payload=payload,
        timeout=int(settings.get('api_timeout') or 30),
    )
    if result['ok']:
        return {'ok': True, 'to': to_number, 'response': result.get('data')}
    err = result.get('error')
    if isinstance(err, dict):
        msg = err.get('error', {}).get('message') or err.get('message') or json.dumps(err, ensure_ascii=False)
    else:
        msg = str(err)
    return {'ok': False, 'to': to_number, 'error': msg}


def test_api_connection(test_phone=None):
    settings = get_whatsapp_api_settings()
    if not settings:
        return {'ok': False, 'error': 'Complete Phone Number ID y token en Configuraciones.'}

    if test_phone:
        probe = send_text_message(test_phone, 'Prueba Factora — API WhatsApp OK.', settings=settings)
        if probe['ok']:
            return {'ok': True, 'message': 'Mensaje de prueba enviado a {}.'.format(probe['to'])}
        return {'ok': False, 'error': probe.get('error', 'Error al enviar prueba.')}

    base = (settings['api_base_url'] or 'https://graph.facebook.com').rstrip('/')
    version = (settings['api_version'] or 'v21.0').strip('/')
    phone_id = settings['phone_number_id']
    url = '{}/{}/{}'.format(base, version, phone_id)
    result = _api_request('GET', url, settings['api_token'], timeout=int(settings.get('api_timeout') or 30))
    if result['ok']:
        return {'ok': True, 'message': 'Conexión OK con Meta Graph API.', 'data': result.get('data')}
    err = result.get('error')
    if isinstance(err, dict):
        msg = err.get('error', {}).get('message') or json.dumps(err, ensure_ascii=False)
    else:
        msg = str(err)
    return {'ok': False, 'error': msg}


def send_bulk_message(campaign):
    from django.utils import timezone
    from core.whatsapp.whatsapp_recipients import get_phones_for_campaign

    phones = get_phones_for_campaign(campaign)

    campaign.total_recipients = len(phones)
    campaign.sent_count = 0
    campaign.failed_count = 0
    campaign.error_log = ''
    campaign.status = campaign.STATUS_SENDING
    campaign.save(update_fields=['total_recipients', 'sent_count', 'failed_count', 'error_log', 'status'])

    if not phones:
        campaign.status = campaign.STATUS_FAILED
        campaign.error_log = 'No hay destinatarios válidos.'
        campaign.save(update_fields=['status', 'error_log'])
        return campaign

    settings = get_whatsapp_api_settings()
    if not settings:
        campaign.status = campaign.STATUS_FAILED
        campaign.error_log = 'API de WhatsApp no configurada.'
        campaign.save(update_fields=['status', 'error_log'])
        return campaign

    errors = []
    for phone in phones:
        result = send_text_message(phone, campaign.message_body, settings=settings)
        if result['ok']:
            campaign.sent_count += 1
        else:
            campaign.failed_count += 1
            errors.append('{}: {}'.format(phone, result.get('error', 'Error')))
        campaign.save(update_fields=['sent_count', 'failed_count'])

    campaign.sent_at = timezone.now()
    if campaign.failed_count == 0:
        campaign.status = campaign.STATUS_COMPLETED
    elif campaign.sent_count == 0:
        campaign.status = campaign.STATUS_FAILED
    else:
        campaign.status = campaign.STATUS_PARTIAL
    campaign.error_log = '\n'.join(errors[:50])
    if len(errors) > 50:
        campaign.error_log += '\n… y {} error(es) más.'.format(len(errors) - 50)
    campaign.save()
    return campaign
