# -*- coding: utf-8 -*-
"""
Crea o actualiza los grupos predeterminados:

  python manage.py ensure_role_groups

  Supervisor     → acceso total (equivalente al rol de Neo en módulos)
  Administrador  → vende/cobra como Asistente + consulta el negocio (sin Seguridad);
                   no puede autorizar cambios con contraseña Neo
  Asistente        → ventas, cobros y caja; sin Seguridad, Reportes ni Bodega
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from core.security.models import Dashboard, Module
from core.security.role_groups import (
    GROUP_SUPERVISOR,
    assign_supervisor_group_only,
    sync_all_role_groups,
)

User = get_user_model()


class Command(BaseCommand):
    help = 'Configura grupos Supervisor, Administrador (ventas/cobros + consulta) y Asistente.'

    def handle(self, *args, **options):
        if not Dashboard.objects.exists():
            Dashboard.objects.create(
                name='Qori',
                icon='fas fa-shopping-cart',
                layout=1,
                card=' ',
                navbar='navbar-dark navbar-primary',
                brand_logo=' ',
                sidebar='sidebar-light-primary',
            )
            self.stdout.write('Dashboard Qori creado.')

        if not Module.objects.filter(is_active=True).exists():
            if Group.objects.filter(name__in=['Administrador', 'Supervisor', 'Cliente']).exists():
                self.stdout.write(
                    self.style.WARNING(
                        'Grupos ya importados pero faltan módulos activos. '
                        'Omitiendo seed; use repair_panel o re-importe security.'
                    )
                )
            elif not Module.objects.exists():
                self.stdout.write('Sin módulos en la base: cargando seed inicial...')
                import core.tests  # noqa: F401
                from django.core.management import call_command

                for cmd in (
                    'ensure_advisory_progress_module',
                    'repair_module_layout',
                    'ensure_collector_module',
                    'ensure_client_report_module',
                    'ensure_contracts_report_module',
                    'ensure_dni_api_module',
                    'ensure_whatsapp_module',
                ):
                    try:
                        call_command(cmd)
                    except Exception as exc:
                        self.stdout.write(self.style.WARNING('{}: {}'.format(cmd, exc)))

        groups = sync_all_role_groups()
        for name, group in groups.items():
            mod_count = group.groupmodule_set.count()
            perm_count = group.grouppermission_set.count()
            self.stdout.write(
                self.style.SUCCESS(
                    'Grupo «{}»: {} módulo(s), {} permiso(s) vinculados.'.format(
                        name, mod_count, perm_count,
                    )
                )
            )

        neo = User.objects.filter(username='Neo').first()
        if neo:
            supervisor = groups.get(GROUP_SUPERVISOR) or Group.objects.filter(
                name=GROUP_SUPERVISOR,
            ).first()
            if supervisor and assign_supervisor_group_only(neo):
                self.stdout.write(
                    'Usuario Neo asignado únicamente al grupo Supervisor.'
                )

        self.stdout.write(self.style.SUCCESS('ensure_role_groups completado.'))
