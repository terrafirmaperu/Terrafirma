"""
Vincula módulos al grupo Administrador y asigna Neo a ese grupo.
Útil tras un deploy con base vacía (solo migraciones, sin seed).
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from core.security.models import Dashboard, GroupModule, GroupPermission, Module

User = get_user_model()

CLIENT_ONLY_URLS = (
    '/pos/crm/client/update/profile/',
    '/pos/crm/sale/client/',
    '/user/update/password/',
)


class Command(BaseCommand):
    help = 'Grupo Administrador: módulos, permisos y usuario Neo.'

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

        group, created = Group.objects.get_or_create(name='Administrador')
        if created:
            self.stdout.write('Grupo Administrador creado.')

        modules = Module.objects.exclude(url__in=CLIENT_ONLY_URLS)
        linked = 0
        for module in modules:
            _, gm_new = GroupModule.objects.get_or_create(group=group, module=module)
            if gm_new:
                linked += 1
            for perm in module.permits.all():
                group.permissions.add(perm)
                GroupPermission.objects.get_or_create(
                    group=group,
                    module=module,
                    permission=perm,
                )

        neo = User.objects.filter(username='Neo').first()
        if neo:
            neo.groups.add(group)
            self.stdout.write('Usuario Neo asignado al grupo Administrador.')
        else:
            self.stdout.write(self.style.WARNING('No existe usuario Neo.'))

        self.stdout.write(
            self.style.SUCCESS(
                'Listo: {} módulo(s) en Administrador ({} enlaces nuevos).'.format(
                    modules.count(), linked
                )
            )
        )
