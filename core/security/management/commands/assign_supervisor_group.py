# -*- coding: utf-8 -*-
"""
Asigna un usuario únicamente al grupo Supervisor.

  python manage.py assign_supervisor_group
  python manage.py assign_supervisor_group --username Neo
"""

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand

from core.security.role_groups import assign_supervisor_group_only

User = get_user_model()


class Command(BaseCommand):
    help = 'Asigna al usuario indicado solo al grupo Supervisor (por defecto Neo).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            default='Neo',
            help='Username exacto (por defecto Neo).',
        )

    def handle(self, *args, **options):
        username = (options.get('username') or 'Neo').strip()
        call_command('ensure_role_groups', verbosity=0)

        user = User.objects.filter(username=username).first()
        if not user:
            self.stdout.write(self.style.ERROR('No existe el usuario «{}».'.format(username)))
            return

        if not assign_supervisor_group_only(user):
            self.stdout.write(
                self.style.ERROR('No existe el grupo Supervisor. Ejecute ensure_role_groups.')
            )
            return

        self.stdout.write(
            self.style.SUCCESS(
                'Usuario «{}» asignado únicamente al grupo Supervisor. Cierre sesión y vuelva a entrar.'.format(
                    username
                )
            )
        )
