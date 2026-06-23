# -*- coding: utf-8 -*-
"""
Registra el módulo Reporte de Contratos bajo Reportes.

  python manage.py ensure_contracts_report_module
  python manage.py ensure_contracts_report_module --group-id 1
"""

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from core.security.models import GroupModule, Module, ModuleType

MODULE_TYPE_NAME = 'Reportes'
MODULE_URL = '/reports/contracts/'


class Command(BaseCommand):
    help = 'Crea el módulo de reporte de contratos en el menú Reportes.'

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
                'name': 'Contratos',
                'moduletype': moduletype,
                'description': (
                    'Clientes con predio y producto vinculados, filtrables por ubicación y producto'
                ),
                'icon': 'fas fa-file-contract',
                'is_vertical': True,
                'is_visible': True,
                'is_active': True,
            },
        )
        module.name = 'Contratos'
        module.moduletype = moduletype
        module.icon = 'fas fa-file-contract'
        module.description = (
            'Clientes con predio y producto vinculados, filtrables por ubicación y producto'
        )
        module.is_active = True
        module.is_visible = True
        module.is_vertical = True
        module.save()

        group_id = options.get('group_id')
        if group_id:
            groups = Group.objects.filter(pk=group_id)
        else:
            groups = Group.objects.all()
        if not groups.exists():
            self.stdout.write(self.style.WARNING('No hay grupos. Asigne el módulo manualmente.'))
            return

        linked = 0
        for group in groups:
            _, gm_created = GroupModule.objects.get_or_create(group=group, module=module)
            if gm_created:
                linked += 1

        from django.core.management import call_command
        call_command('ensure_admin_group_access')

        self.stdout.write(
            self.style.SUCCESS(
                'Módulo «{}» {} — {} grupo(s), {} enlace(s) nuevo(s).'.format(
                    module.name,
                    'creado' if created else 'actualizado',
                    groups.count(),
                    linked,
                )
            )
        )
