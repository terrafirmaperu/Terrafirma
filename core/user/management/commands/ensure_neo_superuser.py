"""
Crea o restablece el usuario Neo (dueño/desarrollador, acceso total).

  python manage.py ensure_neo_superuser
  python manage.py ensure_neo_superuser --password MiClaveSegura
"""

from django.core.management.base import BaseCommand

from core.user.neo_owner import DEFAULT_NEO_PASSWORD, ensure_neo_owner, neo_password


class Command(BaseCommand):
    help = 'Crea o actualiza Neo (superusuario, grupo Supervisor, todos los permisos).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--password',
            default=None,
            help='Contraseña a establecer. Si se omite, usa NEO_ADMIN_PASSWORD o la predeterminada.',
        )
        parser.add_argument(
            '--keep-password',
            action='store_true',
            help='No cambiar la contraseña si Neo ya existe.',
        )

    def handle(self, *args, **options):
        pwd = neo_password(options['password'])
        user, created = ensure_neo_owner(
            password=pwd,
            sync_groups=True,
            reset_password=not options['keep_password'],
        )
        action = 'Creado' if created else 'Actualizado'
        self.stdout.write('Neo quedó solo en el grupo Supervisor con acceso total.')
        self.stdout.write(
            self.style.SUCCESS(
                '{} usuario Neo. Inicie sesión con usuario "Neo" y la contraseña configurada.'.format(
                    action,
                )
            )
        )
        if not options['password'] and not options['keep_password']:
            self.stdout.write(
                'Contraseña aplicada: variable NEO_ADMIN_PASSWORD o predeterminada del sistema.'
            )
