# -*- coding: utf-8 -*-
"""
Registra el tipo de módulo Mensajería (Configuraciones + Mensajes) y la fila de configuración API.

  python manage.py ensure_whatsapp_module
"""

import os

from django.contrib.auth.models import Permission
from django.core.management.base import BaseCommand

from core.security.models import Module, ModuleType
from core.whatsapp.models import WhatsAppApiConfiguration

MODULE_TYPE_NAME = 'Mensajería'
MODULE_TYPE_ICON = 'fab fa-whatsapp'

SUBMODULES = (
    {
        'url': '/whatsapp/config/',
        'name': 'Configuraciones',
        'description': 'API WhatsApp: token, número y parámetros de Meta Cloud API',
        'icon': 'fas fa-cog',
        'model': 'whatsappapiconfiguration',
    },
    {
        'url': '/whatsapp/messages/',
        'name': 'Mensajes',
        'description': 'Envío de mensajes masivos por WhatsApp Business API',
        'icon': 'fas fa-comments',
        'model': 'whatsappbulkmessage',
    },
)


class Command(BaseCommand):
    help = 'Crea el módulo Mensajería con submódulos Configuraciones y Mensajes.'

    def handle(self, *args, **options):
        moduletype, mt_created = ModuleType.objects.get_or_create(
            name=MODULE_TYPE_NAME,
            defaults={'icon': MODULE_TYPE_ICON, 'is_active': True},
        )
        moduletype.icon = MODULE_TYPE_ICON
        moduletype.is_active = True
        moduletype.save()

        created_modules = 0
        for spec in SUBMODULES:
            module, created = Module.objects.get_or_create(
                url=spec['url'],
                defaults={
                    'name': spec['name'],
                    'moduletype': moduletype,
                    'description': spec['description'],
                    'icon': spec['icon'],
                    'is_vertical': True,
                    'is_visible': True,
                    'is_active': True,
                },
            )
            module.name = spec['name']
            module.moduletype = moduletype
            module.description = spec['description']
            module.icon = spec['icon']
            module.is_active = True
            module.is_visible = True
            module.is_vertical = True
            module.save()
            if created:
                created_modules += 1

            for p in Permission.objects.filter(content_type__model=spec['model']):
                module.permits.add(p)

        from core.security.role_groups import sync_all_role_groups
        sync_all_role_groups()

        cfg = WhatsAppApiConfiguration.objects.order_by('id').first()
        if cfg is None:
            env_token = (os.environ.get('WHATSAPP_API_TOKEN') or '').strip()
            env_phone = (os.environ.get('WHATSAPP_PHONE_NUMBER_ID') or '').strip()
            env_display = (os.environ.get('WHATSAPP_PHONE_DISPLAY') or '').strip()
            cfg = WhatsAppApiConfiguration.objects.create(
                provider_name='Meta WhatsApp Cloud API',
                phone_number_id=env_phone,
                phone_number_display=env_display,
                api_token=env_token,
                api_timeout=30,
                is_enabled=True,
                notes='Configurar en Mensajería → Configuraciones',
            )
            cfg_created = True
        else:
            cfg_created = False
            if not cfg.token_configured():
                env_token = (os.environ.get('WHATSAPP_API_TOKEN') or '').strip()
                if env_token:
                    cfg.api_token = env_token
                    cfg.save(update_fields=['api_token'])
            if not (cfg.phone_number_id or '').strip():
                env_phone = (os.environ.get('WHATSAPP_PHONE_NUMBER_ID') or '').strip()
                if env_phone:
                    cfg.phone_number_id = env_phone
                    cfg.save(update_fields=['phone_number_id'])

        self.stdout.write(
            self.style.SUCCESS(
                'Tipo «{}» {} — {} submódulo(s) nuevos — configuración {}.'.format(
                    MODULE_TYPE_NAME,
                    'creado' if mt_created else 'actualizado',
                    created_modules,
                    'creada' if cfg_created else 'existente',
                )
            )
        )
