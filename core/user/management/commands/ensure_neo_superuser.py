"""
Crea o restablece el usuario supervisor Neo (desarrollo / recuperación de acceso).

  python manage.py ensure_neo_superuser
  python manage.py ensure_neo_superuser --password MiClaveSegura
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

User = get_user_model()


class Command(BaseCommand):
    help = 'Crea o actualiza el usuario Neo (staff/superuser) y establece su contraseña.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--password',
            default='lafamilia123456789',
            help='Contraseña a establecer (por defecto la del seed original).',
        )

    def handle(self, *args, **options):
        pwd = options['password']
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
        user.set_password(pwd)
        user.save()
        action = 'Creado' if created else 'Actualizado'
        self.stdout.write(
            self.style.SUCCESS(
                f'{action} usuario Neo. Inicie sesión con usuario exactamente "Neo" y la contraseña indicada.'
            )
        )
