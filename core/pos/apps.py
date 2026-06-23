import sys

from django.apps import AppConfig


class PosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core.pos'

    def ready(self):
        if any(cmd in sys.argv for cmd in ('migrate', 'makemigrations', 'test')):
            return
        from django.conf import settings
        if not settings.DEBUG:
            return
        try:
            self._ensure_sqlite_client_marital_status()
        except Exception:
            pass

    @staticmethod
    def _ensure_sqlite_client_marital_status():
        from django.core.management import call_command
        from django.db import connection

        call_command('migrate', verbosity=0, interactive=False)
        if connection.vendor != 'sqlite':
            return
        with connection.cursor() as cur:
            cur.execute('PRAGMA table_info(pos_client)')
            cols = [row[1] for row in cur.fetchall()]
            if 'marital_status' in cols:
                return
            cur.execute(
                "ALTER TABLE pos_client ADD COLUMN marital_status "
                "varchar(20) NOT NULL DEFAULT ''"
            )
            cur.execute(
                "SELECT 1 FROM django_migrations WHERE app='pos' "
                "AND name='0037_client_marital_status'"
            )
            if not cur.fetchone():
                cur.execute(
                    "INSERT INTO django_migrations (app, name, applied) "
                    "VALUES ('pos', '0037_client_marital_status', datetime('now'))"
                )
