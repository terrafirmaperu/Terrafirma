"""
Reinicia datos del sistema conservando usuarios del backup.

  python manage.py reset_db_keep_users
  python manage.py reset_db_keep_users --backup db/users_backup.json
"""

import json
import os

from django.contrib.auth.models import Group
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import connection

from core.user.models import User


class Command(BaseCommand):
    help = 'Vacía la base, ejecuta seed y restaura usuarios del archivo backup.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--backup',
            default='db/users_backup.json',
            help='Ruta al JSON de usuarios (relativa a app/).',
        )
        parser.add_argument(
            '--skip-seed',
            action='store_true',
            help='Solo flush + migrate + restaurar usuarios (sin core/tests.py).',
        )

    def handle(self, *args, **options):
        from django.conf import settings

        app_dir = settings.BASE_DIR
        backup_path = options['backup']
        if not os.path.isabs(backup_path):
            backup_path = os.path.join(app_dir, backup_path)

        if not os.path.isfile(backup_path):
            self.stdout.write(self.style.ERROR('No existe backup: {}'.format(backup_path)))
            return

        with open(backup_path, encoding='utf-8') as fh:
            users_data = json.load(fh)

        self.stdout.write('Vaciando base de datos (flush)...')
        call_command('flush', '--noinput')

        self.stdout.write('Aplicando migraciones...')
        call_command('migrate', '--noinput')

        if not options['skip_seed']:
            self.stdout.write('Ejecutando seed (core/tests.py)...')
            import sys

            if app_dir not in sys.path:
                sys.path.insert(0, app_dir)
            import core.tests  # noqa: F401

            self.stdout.write('Módulo de asesoría...')
            call_command('ensure_advisory_progress_module', '--group-id=1')
            self.stdout.write('Orden de módulos...')
            call_command('repair_module_layout')

        restored = self._restore_users(users_data)
        self.stdout.write(self.style.SUCCESS('Listo. Usuarios restaurados: {}.'.format(', '.join(restored))))

    def _restore_users(self, users_data):
        restored = []
        for row in users_data:
            username = (row.get('username') or '').strip()
            if not username:
                continue
            user, created = User.objects.update_or_create(
                username=username,
                defaults={
                    'dni': row.get('dni') or username,
                    'email': row.get('email') or '',
                    'first_name': row.get('first_name') or '',
                    'last_name': row.get('last_name') or '',
                    'is_active': bool(row.get('is_active', True)),
                    'is_staff': bool(row.get('is_staff', False)),
                    'is_superuser': bool(row.get('is_superuser', False)),
                    'is_change_password': bool(row.get('is_change_password', False)),
                },
            )
            pwd_hash = row.get('password_hash')
            if pwd_hash:
                user.password = pwd_hash
                user.save(update_fields=['password'])

            user.groups.clear()
            for group_name in row.get('groups') or []:
                group = Group.objects.filter(name=group_name).first()
                if group:
                    user.groups.add(group)

            restored.append(username)
            action = 'creado' if created else 'actualizado'
            self.stdout.write('  · {} ({})'.format(username, action))
        return restored
