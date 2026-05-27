"""Envío del formulario de contacto del sitio público."""

import logging

from django.conf import settings
from django.core.mail import EmailMessage, get_connection

from core.marketing.forms import SERVICE_CHOICES

logger = logging.getLogger(__name__)

_SERVICE_LABELS = dict(SERVICE_CHOICES)


def _service_label(code):
    if not code:
        return 'No indicado'
    return _SERVICE_LABELS.get(code, code)


def send_marketing_contact_email(cleaned_data, request=None):
    """
    Envía el mensaje del formulario a MARKETING_CONTACT_EMAIL (terrafirmaperu@gmail.com).
    """
    recipient = getattr(
        settings,
        'MARKETING_CONTACT_EMAIL',
        'terrafirmaperu@gmail.com',
    )
    brand = getattr(settings, 'SITE_NAME', 'Terrafirma')
    name = cleaned_data['name'].strip()
    email = cleaned_data['email'].strip().lower()
    phone = (cleaned_data.get('phone') or '').strip() or '—'
    service = _service_label(cleaned_data.get('service'))
    message = cleaned_data['message'].strip()

    subject = '[{}] Contacto web — {}'.format(brand, service)
    body_lines = [
        'Nuevo mensaje desde el formulario de contacto',
        '',
        'Nombre: {}'.format(name),
        'Correo: {}'.format(email),
        'Teléfono: {}'.format(phone),
        'Servicio: {}'.format(service),
        '',
        'Mensaje:',
        message,
        '',
    ]
    if request is not None:
        body_lines.extend([
            '—',
            'IP: {}'.format(_client_ip(request)),
            'Navegador: {}'.format((request.META.get('HTTP_USER_AGENT') or '')[:300]),
        ])
    body = '\n'.join(body_lines)

    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None) or settings.EMAIL_HOST_USER
    mail = EmailMessage(
        subject=subject,
        body=body,
        from_email=from_email,
        to=[recipient],
        reply_to=[email],
    )

    connection = get_connection()
    if not getattr(settings, 'EMAIL_HOST_PASSWORD', '') and settings.DEBUG:
        connection = get_connection(backend='django.core.mail.backends.console.EmailBackend')

    mail.connection = connection
    mail.send(fail_silently=False)


def _client_ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')
