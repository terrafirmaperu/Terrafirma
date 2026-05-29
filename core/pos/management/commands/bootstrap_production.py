"""
Prepara el servidor tras el primer deploy o una actualización.

  DJANGO_SETTINGS_MODULE=config.production python manage.py bootstrap_production
  RUN_INITIAL_SEED=1 ... bootstrap_production   # carga módulos iniciales (solo 1ª vez)
"""

import os

from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Migrate, collectstatic, módulos de seguridad y usuario admin opcional.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--seed',
            action='store_true',
            help='Ejecutar seed inicial (core/tests.py). Equivalente a RUN_INITIAL_SEED=1.',
        )
        parser.add_argument(
            '--skip-static',
            action='store_true',
            help='No ejecutar collectstatic.',
        )

    def handle(self, *args, **options):
        self.stdout.write('Aplicando migraciones...')
        call_command('migrate', '--noinput')

        if not options['skip_static']:
            self.stdout.write('Recopilando archivos estáticos...')
            call_command('collectstatic', '--noinput', verbosity=0)

        from core.security.models import Module

        run_seed = options['seed'] or os.environ.get('RUN_INITIAL_SEED', '').strip() == '1'
        needs_modules = not Module.objects.exists()
        if run_seed or needs_modules:
            if needs_modules:
                self.stdout.write('Cargando datos iniciales (seed)...')
                import core.tests  # noqa: F401
            else:
                self.stdout.write('Módulos ya existen; omitiendo import core.tests.')
            call_command('ensure_advisory_progress_module', '--group-id=1')
            call_command('repair_module_layout')
            try:
                call_command('ensure_client_report_module', '--group-id=1')
            except Exception as exc:
                self.stdout.write(self.style.WARNING('Reporte cliente: {}'.format(exc)))
        else:
            self.stdout.write('Módulos de asesoría / layout...')
            try:
                call_command('ensure_advisory_progress_module', '--group-id=1')
                call_command('repair_module_layout')
            except Exception as exc:
                self.stdout.write(self.style.WARNING(str(exc)))

        call_command('ensure_admin_group_access')

        neo_pwd = os.environ.get('NEO_ADMIN_PASSWORD', '').strip()
        if neo_pwd:
            call_command('ensure_neo_superuser', password=neo_pwd)
            self.stdout.write(self.style.SUCCESS('Usuario Neo configurado.'))
        else:
            self.stdout.write(
                'Sin NEO_ADMIN_PASSWORD: omitido ensure_neo_superuser.'
            )

        self.stdout.write(self.style.SUCCESS('bootstrap_production completado.'))
