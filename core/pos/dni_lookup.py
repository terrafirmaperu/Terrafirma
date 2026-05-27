import requests
from urllib.parse import urlencode

from config import settings


def _split_full_name(full_name):
    parts = [p for p in (full_name or '').strip().split(' ') if p]
    if not parts:
        return '', ''
    if len(parts) == 1:
        return parts[0], ''
    return parts[0], ' '.join(parts[1:])


def lookup_dni_data(dni):
    dni = (dni or '').strip()
    if not dni:
        return {'error': 'Debe ingresar un DNI'}
    if not dni.isdigit():
        return {'error': 'El DNI solo debe contener números'}
    if len(dni) < 7 or len(dni) > 12:
        return {'error': 'El DNI debe tener entre 7 y 12 dígitos'}

    url_template = getattr(settings, 'DNI_API_URL', 'https://api.decolecta.com/v1/reniec/dni?numero={dni}')
    token = (getattr(settings, 'DNI_API_TOKEN', '') or '').strip()
    timeout = int(getattr(settings, 'DNI_API_TIMEOUT', 12))

    url = url_template.format(dni=dni)

    def do_request(request_url, headers=None):
        try:
            return requests.get(request_url, headers=headers or {}, timeout=timeout)
        except requests.RequestException:
            return None

    # 1) Intento principal: Bearer token (esquema usado por varios proveedores)
    headers = {}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    response = do_request(url, headers=headers)
    if response is None:
        return {'error': 'No se pudo consultar el API de DNI en este momento'}

    # 2) Fallback: algunos proveedores esperan ?token=... en querystring
    if response.status_code in (401, 403) and token:
        sep = '&' if '?' in url else '?'
        url_with_token = f'{url}{sep}{urlencode({"token": token})}'
        response_alt = do_request(url_with_token, headers={})
        if response_alt is not None:
            response = response_alt

    if response.status_code in (401, 403):
        return {
            'error': (
                'El API de DNI rechazó la credencial (401/403). '
                'Configure un token válido en DNI_API_TOKEN.'
            )
        }
    if response.status_code != 200:
        return {'error': f'El API de DNI respondió con estado {response.status_code}'}

    try:
        payload = response.json()
    except ValueError:
        return {'error': 'El API de DNI devolvió una respuesta no válida'}

    # Algunos proveedores devuelven {"success":false,"message":"..."} con HTTP 200
    if payload.get('success') is False or payload.get('ok') is False:
        return {'error': payload.get('message') or payload.get('error') or 'No se pudo consultar el DNI'}

    first_name = ''
    last_name = ''

    # Formato tipo apisperu
    nombres = (payload.get('nombres') or '').strip()
    ap_paterno = (payload.get('apellidoPaterno') or '').strip()
    ap_materno = (payload.get('apellidoMaterno') or '').strip()
    if nombres or ap_paterno or ap_materno:
        first_name = nombres
        last_name = ' '.join([v for v in [ap_paterno, ap_materno] if v]).strip()

    # Formato Decolecta
    if not first_name and not last_name:
        first_name = (payload.get('first_name') or '').strip()
        ap1 = (payload.get('first_last_name') or '').strip()
        ap2 = (payload.get('second_last_name') or '').strip()
        if first_name or ap1 or ap2:
            last_name = ' '.join([v for v in [ap1, ap2] if v]).strip()

    # Fallback por nombre completo
    if not first_name and not last_name:
        full_name = (
            payload.get('full_name')
            or payload.get('nombreCompleto')
            or payload.get('nombre')
            or payload.get('name')
            or ''
        )
        first_name, last_name = _split_full_name(full_name)

    if not first_name and not last_name:
        return {'error': 'No se encontraron datos para el DNI consultado'}

    return {
        'first_name': first_name,
        'last_name': last_name,
        'dni': dni,
    }
