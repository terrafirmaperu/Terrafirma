"""Textos y datos públicos del sitio (Terrafirma)."""

from urllib.parse import quote

from django.conf import settings
from django.urls import reverse


_DEFAULT = {
    'brand_name': 'Terrafirma',
    'legal_name': 'Terrafirma Asesoría y Consultoría S.A.C.',
    'tagline': 'Asesoría en procesos de titulación predial',
    'ruc': '921047681',
    'address': 'Huancavelica, Perú',
    'phone_mobile': '921 047 681',
    'whatsapp_phone': '921047681',
    'phone_office': '067 123456',
    'email': 'terrafirmaperu@gmail.com',
    'website': 'https://terrafirmaperu.com',
    'hours': 'Lunes a viernes · 9:00 a 18:00',
    'regions': 'Costa, Sierra y Selva',
}

VALUES = (
    {
        'icon': 'bi-shield-check',
        'title': 'Cumplimiento normativo',
        'text': 'Trabajamos conforme a la legislación vigente en materia de saneamiento físico-legal y catastro.',
    },
    {
        'icon': 'bi-people',
        'title': 'Acompañamiento cercano',
        'text': 'Cada cliente conoce el estado de su trámite y los documentos que debe aportar en cada etapa.',
    },
    {
        'icon': 'bi-geo-alt',
        'title': 'Cobertura nacional',
        'text': 'Experiencia en expedientes en distintas regiones del país, adaptándonos a los requisitos locales.',
    },
    {
        'icon': 'bi-graph-up-arrow',
        'title': 'Resultados medibles',
        'text': 'Seguimiento por etapas, plazos acordados y entregables claros desde el inicio del servicio.',
    },
)

SERVICES = (
    {
        'icon': 'bi-building',
        'title': 'Saneamiento físico-legal',
        'text': 'Regularización de predios urbanos y rurales ante registros públicos y municipalidades.',
    },
    {
        'icon': 'bi-file-earmark-text',
        'title': 'Titulación y formalización',
        'text': 'Armado de expedientes, memoria descriptiva, planos y trámites ante SUNARP y entidades competentes.',
    },
    {
        'icon': 'bi-map',
        'title': 'Proyectos en cartera',
        'text': 'Acompañamiento a urbanizaciones, lotizaciones y proyectos con avance por etapas documentado.',
    },
    {
        'icon': 'bi-clipboard-data',
        'title': 'Catastro y actualización',
        'text': 'Levantamiento de información, confrontación de linderos y apoyo en procesos catastrales.',
    },
    {
        'icon': 'bi-hammer',
        'title': 'Gestión municipal',
        'text': 'Licencias, habilitaciones urbanas y coordinación con oficinas de registro y catastro local.',
    },
    {
        'icon': 'bi-house-door',
        'title': 'Programas habitacionales',
        'text': 'Orientación para Fondo Mi Vivienda, Techo Propio y créditos vinculados a saneamiento.',
    },
)

ADVISORY_SECTIONS = (
    {
        'slug': 'titulacion',
        'icon': 'bi-geo-alt-fill',
        'title': 'Titulación predial',
        'lead': 'Saneamiento y regularización de predios con expediente técnico-legal completo.',
        'items': (
            'Diagnóstico documental del predio y titulares.',
            'Elaboración de memoria descriptiva y planos conforme a norma.',
            'Gestión ante municipalidad, catastro y SUNARP según corresponda.',
            'Seguimiento hasta la inscripción o el estado que defina el expediente.',
        ),
    },
    {
        'slug': 'municipales',
        'icon': 'bi-bank',
        'title': 'Asesorías municipales',
        'lead': 'Trámites y coordinación con entidades locales de su jurisdicción.',
        'items': (
            'Certificados de parámetros urbanísticos y zonificación.',
            'Habilitaciones, licencias de edificación y conformidades.',
            'Atención de observaciones y subsanación de expedientes.',
            'Representación y asesoría en mesas técnicas cuando aplique.',
        ),
    },
    {
        'slug': 'topografia',
        'icon': 'bi-rulers',
        'title': 'Topografía, ingeniería y seguridad',
        'lead': 'Soporte técnico para respaldar su trámite o proyecto inmobiliario.',
        'items': (
            'Levantamientos topográficos y planialtimétricos.',
            'Curvas de nivel, modelos de terreno y replanteos.',
            'Estudios de suelo y seguridad según alcance del proyecto.',
            'Batimetría y trabajos especiales coordinados con especialistas.',
        ),
    },
    {
        'slug': 'vivienda',
        'icon': 'bi-house-heart',
        'title': 'Fondo Mi Vivienda y Techo Propio',
        'lead': 'Orientación para acceder a beneficios habitacionales del Estado.',
        'items': (
            'Revisión de requisitos y documentación del postulante.',
            'Alineación del predio con condiciones del programa.',
            'Acompañamiento en etapas de evaluación y desembolso.',
            'Coordinación con entidades financieras y municipales.',
        ),
    },
)

PORTFOLIO_ITEMS = (
    {
        'title': 'Urbanización en expansión',
        'location': 'Sierra central',
        'status': 'En saneamiento',
        'text': 'Lotización con más de 120 predios en proceso de regularización por etapas.',
    },
    {
        'title': 'Núcleo poblacional rural',
        'location': 'Selva alta',
        'status': 'Titulación avanzada',
        'text': 'Formalización de posesiones con memoria descriptiva y plano perimétrico aprobado.',
    },
    {
        'title': 'Proyecto costero',
        'location': 'Costa norte',
        'status': 'Gestión municipal',
        'text': 'Habilitación urbana y catastro en coordinación con la municipalidad provincial.',
    },
)


def _company_defaults():
    try:
        from core.pos.models import Company

        company = Company.objects.order_by('-id').first()
    except Exception:
        company = None
    if not company:
        return dict(_DEFAULT)
    return {
        'brand_name': (company.name or _DEFAULT['brand_name']).strip(),
        'legal_name': (company.name or _DEFAULT['legal_name']).strip(),
        'tagline': (company.desc or _DEFAULT['tagline']).strip(),
        'ruc': (company.ruc or _DEFAULT['ruc']).strip(),
        'address': (company.address or _DEFAULT['address']).strip(),
        'phone_mobile': (company.mobile or _DEFAULT['phone_mobile']).strip(),
        'phone_office': (company.phone or _DEFAULT['phone_office']).strip(),
        'email': (company.email or _DEFAULT['email']).strip(),
        'website': (company.website or _DEFAULT['website']).strip(),
        'hours': _DEFAULT['hours'],
        'regions': _DEFAULT['regions'],
    }


def _phone_digits(raw):
    return ''.join(c for c in (raw or '') if c.isdigit())


def _phone_e164_pe(raw):
    """Número en formato internacional Perú (51 + 9 dígitos celular)."""
    digits = _phone_digits(raw)
    if len(digits) == 9:
        return '51{}'.format(digits)
    if len(digits) == 11 and digits.startswith('51'):
        return digits
    return digits


def get_contact_links(info=None):
    """Enlaces tel:, WhatsApp y formulario de contacto para el FAB flotante."""
    info = dict(info or _company_defaults())
    mobile = info.get('phone_mobile') or _DEFAULT['phone_mobile']
    office = info.get('phone_office') or _DEFAULT['phone_office']
    whatsapp = info.get('whatsapp_phone') or _DEFAULT['whatsapp_phone']
    brand = info.get('brand_name') or _DEFAULT['brand_name']

    e164_wa = _phone_e164_pe(whatsapp)
    e164_tel = _phone_e164_pe(mobile) or e164_wa or _phone_e164_pe(office)
    tel_href = 'tel:+{}'.format(e164_tel) if e164_tel else ''
    wa_text = 'Hola {}, deseo información sobre sus servicios.'.format(brand)
    wa_href = ''
    if e164_wa:
        wa_href = 'https://wa.me/{}?text={}'.format(e164_wa, quote(wa_text))

    return {
        'contact_tel_href': tel_href,
        'contact_tel_label': mobile or office,
        'contact_whatsapp_href': wa_href,
        'contact_form_href': reverse('marketing_contacto'),
    }


def get_site_info():
    info = _company_defaults()
    info['whatsapp_phone'] = _DEFAULT['whatsapp_phone']
    info['site_name'] = getattr(settings, 'SITE_NAME', None) or info['brand_name']
    info.update(get_contact_links(info))
    return info


def get_marketing_page_context():
    info = get_site_info()
    return {
        'site_info': info,
        'company_values': VALUES,
        'marketing_services': SERVICES,
        'advisory_sections': ADVISORY_SECTIONS,
        'portfolio_items': PORTFOLIO_ITEMS,
    }
