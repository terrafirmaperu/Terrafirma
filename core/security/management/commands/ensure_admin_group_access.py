"""
Vincula módulos al grupo Administrador y asigna Neo a ese grupo.
Útil tras un deploy con base vacía (solo migraciones, sin seed).

Nota: use ensure_role_groups para Supervisor / Administrador / Asistente.
"""

from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Alias de ensure_role_groups (grupos predeterminados y Neo en Supervisor).'

    def handle(self, *args, **options):
        call_command('ensure_role_groups', verbosity=options.get('verbosity', 1))
