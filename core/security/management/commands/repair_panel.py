# -*- coding: utf-8 -*-
"""Repara panel vacío: módulos, grupos y usuario Neo."""

from django.core.management.base import BaseCommand

from core.security.models import GroupModule, Module
from core.security.role_groups import GROUP_SUPERVISOR, panel_module_types_for_group
from core.user.neo_owner import ensure_neo_owner


class Command(BaseCommand):
    help = 'Repara módulos del panel (Supervisor / Neo) y muestra un resumen.'

    def handle(self, *args, **options):
        from django.contrib.auth.models import Group

        from core.security.role_groups import repair_supervisor_module_links

        user, _ = ensure_neo_owner(sync_groups=True, reset_password=False)
        repair_supervisor_module_links(user)

        sup = Group.objects.filter(name=GROUP_SUPERVISOR).first()
        mod_count = Module.objects.filter(is_active=True).count()
        link_count = GroupModule.objects.filter(group=sup).count() if sup else 0
        types_count = panel_module_types_for_group(sup).count() if sup else 0

        self.stdout.write('Módulos activos: {}'.format(mod_count))
        self.stdout.write('Vínculos grupo Supervisor: {}'.format(link_count))
        self.stdout.write('Tipos visibles en panel: {}'.format(types_count))
        self.stdout.write('Neo superusuario: {}'.format(user.is_superuser))
        self.stdout.write('Neo grupos: {}'.format(list(user.groups.values_list('name', flat=True))))

        if mod_count == 0:
            self.stdout.write(self.style.ERROR(
                'No hay módulos. Ejecute: python manage.py ensure_role_groups'
            ))
        elif types_count == 0:
            self.stdout.write(self.style.WARNING(
                'Hay módulos pero el panel no los ve. Cierre sesión y vuelva a entrar.'
            ))
        else:
            self.stdout.write(self.style.SUCCESS('Panel reparado. Recargue /dashboard/.'))
