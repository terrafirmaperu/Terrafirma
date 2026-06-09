"""
Crea o restablece el usuario supervisor Neo (desarrollo / recuperación de acceso).

  python manage.py ensure_neo_superuser
  python manage.py ensure_neo_superuser --password MiClaveSegura
"""

import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

User = get_user_model()

# Contraseña por defecto del supervisor (producción Terrafirma). Prioridad: --password → NEO_ADMIN_PASSWORD.
DEFAULT_NEO_PASSWORD = 'Enyaeslamejor'


class Command(BaseCommand):
    help = 'Crea o actualiza el usuario Neo (staff/superuser) y establece su contraseña.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--password',
            default=None,
            help='Contraseña a establecer. Si se omite, usa NEO_ADMIN_PASSWORD.',
        )

    def handle(self, *args, **options):
        pwd = (
            options['password']
            or os.environ.get('NEO_ADMIN_PASSWORD', '').strip()
            or DEFAULT_NEO_PASSWORD
        )
        defaults = {
            'dni': '0000000000001',
            'email': 'neo@factora.local',
            'first_name': 'Supervisor',
            'last_name': 'Sistema',
            'is_active': True,
            'is_staff': True,
            'is_superuser': True,
            'is_change_password': False,
        }
        user, created = User.objects.update_or_create(username='Neo', defaults=defaults)
        user.is_active = True
        user.is_staff = True
        user.is_superuser = True
        user.is_change_password = False
        user.set_password(pwd)
        user.save()
        from django.contrib.auth.models import Group
        admin_group = Group.objects.filter(name='Administrador').first()
        if admin_group:
            user.groups.add(admin_group)
        from django.core.management import call_command
        call_command('ensure_admin_group_access')
        action = 'Creado' if created else 'Actualizado'
        self.stdout.write(
            self.style.SUCCESS(
                f'{action} usuario Neo. Inicie sesión con usuario exactamente "Neo" y la contraseña indicada.'
            )
        )
