# -*- coding: utf-8 -*-
"""
Registra el módulo Reporte de Clientes bajo Reportes.

  python manage.py ensure_client_report_module
  python manage.py ensure_client_report_module --group-id 1
"""

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from core.security.models import GroupModule, Module, ModuleType

MODULE_TYPE_NAME = 'Reportes'
MODULE_URL = '/reports/clients/'


class Command(BaseCommand):
    help = 'Crea el módulo de reporte de clientes en el menú Reportes.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--group-id',
            type=int,
            default=None,
            help='ID del grupo al que asignar el módulo (por defecto el primero).',
        )

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
                'name': 'Clientes',
                'moduletype': moduletype,
                'description': (
                    'Listado de clientes con filtros por comunidad, centro poblado, '
                    'provincia y distrito'
                ),
                'icon': 'fas fa-users',
                'is_vertical': True,
                'is_visible': True,
                'is_active': True,
            },
        )
        module.name = 'Clientes'
        module.moduletype = moduletype
        module.icon = 'fas fa-users'
        module.is_active = True
        module.is_visible = True
        module.is_vertical = True
        module.save()

        group_id = options.get('group_id')
        group = Group.objects.filter(pk=group_id).first() if group_id else Group.objects.order_by('id').first()
        if not group:
            self.stdout.write(self.style.WARNING('No hay grupos. Asigne el módulo manualmente.'))
            return

        gm, gm_created = GroupModule.objects.get_or_create(group=group, module=module)
        self.stdout.write(
            self.style.SUCCESS(
                'Módulo «{}» {} — grupo «{}» (GroupModule {}).'.format(
                    module.name,
                    'creado' if created else 'actualizado',
                    group.name,
                    'nuevo' if gm_created else 'existente',
                )
            )
        )
