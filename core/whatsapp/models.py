from datetime import datetime

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.forms.models import model_to_dict

User = get_user_model()


class WhatsAppApiConfiguration(models.Model):
    """Configuración singleton de WhatsApp Business Cloud API (Meta)."""

    DEFAULT_API_BASE = 'https://graph.facebook.com'
    DEFAULT_API_VERSION = 'v21.0'

    provider_name = models.CharField(max_length=80, default='Meta WhatsApp Cloud API', verbose_name='Proveedor')
    phone_number_id = models.CharField(
        max_length=64,
        blank=True,
        default='',
        verbose_name='ID del número (Phone Number ID)',
        help_text='Identificador del número en Meta Business / WhatsApp Cloud API.',
    )
    phone_number_display = models.CharField(
        max_length=20,
        blank=True,
        default='',
        verbose_name='Número visible',
        help_text='Ej. 921047681 o +51921047681 (solo referencia en pantalla).',
    )
    business_account_id = models.CharField(
        max_length=64,
        blank=True,
        default='',
        verbose_name='WhatsApp Business Account ID',
    )
    api_base_url = models.CharField(
        max_length=200,
        default=DEFAULT_API_BASE,
        verbose_name='URL base API',
    )
    api_version = models.CharField(
        max_length=20,
        default=DEFAULT_API_VERSION,
        verbose_name='Versión API',
    )
    api_token = models.CharField(max_length=500, blank=True, default='', verbose_name='Token de acceso')
    api_timeout = models.PositiveSmallIntegerField(default=30, verbose_name='Tiempo de espera (segundos)')
    is_enabled = models.BooleanField(default=True, verbose_name='API habilitada')
    notes = models.CharField(max_length=500, blank=True, default='', verbose_name='Notas')

    def __str__(self):
        label = self.phone_number_display or self.phone_number_id or 'Sin número'
        return '{} — {}'.format(self.provider_name, label)

    def token_configured(self):
        return bool((self.api_token or '').strip())

    def get_messages_endpoint(self):
        base = (self.api_base_url or self.DEFAULT_API_BASE).rstrip('/')
        version = (self.api_version or self.DEFAULT_API_VERSION).strip('/')
        phone_id = (self.phone_number_id or '').strip()
        return '{}/{}/{}/messages'.format(base, version, phone_id)

    def toJSON(self):
        item = model_to_dict(self)
        item['token_configured'] = self.token_configured()
        item['api_token'] = '********' if self.token_configured() else ''
        item['messages_endpoint'] = self.get_messages_endpoint()
        return item

    @classmethod
    def get_solo(cls):
        row = cls.objects.order_by('id').first()
        if row:
            return row
        return cls(
            provider_name='Meta WhatsApp Cloud API',
            api_base_url=cls.DEFAULT_API_BASE,
            api_version=cls.DEFAULT_API_VERSION,
            api_timeout=30,
            is_enabled=True,
        )

    class Meta:
        verbose_name = 'Configuración API WhatsApp'
        verbose_name_plural = 'Configuración API WhatsApp'
        default_permissions = ()
        permissions = (
            ('view_whatsappapiconfiguration', 'Can view Configuración API WhatsApp'),
            ('change_whatsappapiconfiguration', 'Can change Configuración API WhatsApp'),
        )


class WhatsAppBulkMessage(models.Model):
    STATUS_DRAFT = 'draft'
    STATUS_SENDING = 'sending'
    STATUS_COMPLETED = 'completed'
    STATUS_FAILED = 'failed'
    STATUS_PARTIAL = 'partial'
    STATUS_CHOICES = (
        (STATUS_DRAFT, 'Borrador'),
        (STATUS_SENDING, 'Enviando'),
        (STATUS_COMPLETED, 'Completado'),
        (STATUS_PARTIAL, 'Parcial'),
        (STATUS_FAILED, 'Fallido'),
    )

    SOURCE_MANUAL = 'manual'
    SOURCE_CLIENTS = 'clients'
    SOURCE_FILTER = 'filter'
    SOURCE_CHOICES = (
        (SOURCE_MANUAL, 'Lista manual'),
        (SOURCE_CLIENTS, 'Todos los clientes con teléfono'),
        (SOURCE_FILTER, 'Filtrar clientes'),
    )

    name = models.CharField(max_length=120, verbose_name='Nombre / asunto')
    message_body = models.TextField(verbose_name='Mensaje')
    recipient_source = models.CharField(
        max_length=20,
        choices=SOURCE_CHOICES,
        default=SOURCE_MANUAL,
        verbose_name='Destinatarios',
    )
    recipients_text = models.TextField(
        blank=True,
        default='',
        verbose_name='Teléfonos (manual)',
        help_text='Un número por línea o separados por coma. Formato Perú: 9 dígitos o 51...',
    )
    filter_criteria = models.TextField(
        blank=True,
        default='{}',
        verbose_name='Criterios de filtro',
        help_text='JSON con comunidad, deuda, pagadores, ubicación, producto, etc.',
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT, verbose_name='Estado')
    total_recipients = models.PositiveIntegerField(default=0, verbose_name='Total destinatarios')
    sent_count = models.PositiveIntegerField(default=0, verbose_name='Enviados')
    failed_count = models.PositiveIntegerField(default=0, verbose_name='Fallidos')
    error_log = models.TextField(blank=True, default='', verbose_name='Errores')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Usuario',
    )
    date_joined = models.DateField(default=datetime.now, verbose_name='Fecha')
    hour = models.TimeField(default=datetime.now, verbose_name='Hora')
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name='Enviado el')

    def __str__(self):
        return self.name

    def toJSON(self):
        item = model_to_dict(self)
        item['user'] = self.user.get_full_name() if self.user_id else ''
        item['date_joined'] = self.date_joined.strftime('%d-%m-%Y')
        item['hour'] = self.hour.strftime('%H:%M')
        item['status_label'] = self.get_status_display()
        item['recipient_source_label'] = self.get_recipient_source_display()
        from core.whatsapp.whatsapp_recipients import filter_criteria_label
        item['filter_summary'] = filter_criteria_label(self.filter_criteria)
        item['sent_at'] = self.sent_at.strftime('%d-%m-%Y %H:%M') if self.sent_at else ''
        preview = (self.message_body or '')[:80]
        item['message_preview'] = preview + ('…' if len(self.message_body or '') > 80 else '')
        return item

    class Meta:
        verbose_name = 'Mensaje masivo WhatsApp'
        verbose_name_plural = 'Mensajes masivos WhatsApp'
        default_permissions = ()
        permissions = (
            ('view_whatsappbulkmessage', 'Can view Mensajes masivos WhatsApp'),
            ('add_whatsappbulkmessage', 'Can add Mensajes masivos WhatsApp'),
            ('change_whatsappbulkmessage', 'Can change Mensajes masivos WhatsApp'),
            ('delete_whatsappbulkmessage', 'Can delete Mensajes masivos WhatsApp'),
        )
        ordering = ['-id']
