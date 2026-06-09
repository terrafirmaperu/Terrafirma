# -*- coding: utf-8 -*-
"""
Registra el submódulo Config. API DNI bajo Seguridad y crea la fila de configuración.

  python manage.py ensure_dni_api_module
"""

import os

from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand

from core.security.models import DniApiConfiguration, GroupModule, Module, ModuleType


MODULE_TYPE_NAME = 'Seguridad'
MODULE_URL = '/security/api/dni/update/'


class Command(BaseCommand):
    help = 'Crea el submódulo de configuración API DNI en Seguridad.'

    def handle(self, *args, **options):
        moduletype = ModuleType.objects.filter(name=MODULE_TYPE_NAME).first()
        if not moduletype:
            self.stdout.write(
                self.style.ERROR(
                    'No existe el tipo «{}». Ejecute el seed (core/tests.py) primero.'.format(
                        MODULE_TYPE_NAME
                    )
                )
            )
            return

        module, created = Module.objects.get_or_create(
            url=MODULE_URL,
            defaults={
                'name': 'Config. API DNI',
                'moduletype': moduletype,
                'description': 'API Key y URL para consulta RENIEC al registrar clientes',
                'icon': 'fas fa-id-card',
                'is_vertical': True,
                'is_visible': True,
                'is_active': True,
            },
        )
        module.name = 'Config. API DNI'
        module.moduletype = moduletype
        module.icon = 'fas fa-id-card'
        module.description = 'API Key y URL para consulta RENIEC al registrar clientes'
        module.is_active = True
        module.is_visible = True
        module.is_vertical = True
        module.save()

        model_name = DniApiConfiguration._meta.label.split('.')[1].lower()
        for p in Permission.objects.filter(content_type__model=model_name):
            module.permits.add(p)

        cfg = DniApiConfiguration.objects.order_by('id').first()
        if cfg is None:
            env_token = (os.environ.get('DNI_API_TOKEN') or '').strip()
            cfg = DniApiConfiguration.objects.create(
                provider_name='Decolecta',
                api_url=DniApiConfiguration.DEFAULT_API_URL,
                api_token=env_token,
                api_timeout=12,
                is_enabled=True,
                notes='Cuenta terrafirmaperu@gmail.com',
            )
            cfg_created = True
        else:
            cfg_created = False
            if not cfg.token_configured():
                env_token = (os.environ.get('DNI_API_TOKEN') or '').strip()
                if env_token:
                    cfg.api_token = env_token
                    cfg.save(update_fields=['api_token'])

        for group in Group.objects.all():
            GroupModule.objects.get_or_create(group=group, module=module)

        from django.core.management import call_command
        call_command('ensure_admin_group_access')

        self.stdout.write(
            self.style.SUCCESS(
                'Módulo «{}» {} — configuración {}.'.format(
                    module.name,
                    'creado' if created else 'actualizado',
                    'creada' if cfg_created else 'existente',
                )
            )
        )
