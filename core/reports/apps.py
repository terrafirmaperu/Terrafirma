import sys

from django.apps import AppConfig


class ReportsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core.reports'

    def ready(self):
        if any(cmd in sys.argv for cmd in ('migrate', 'makemigrations', 'test', 'shell')):
            return
        from django.conf import settings
        if not settings.DEBUG:
            return
        try:
            self._ensure_contracts_report_module()
        except Exception:
            pass

    @staticmethod
    def _ensure_contracts_report_module():
        from django.core.management import call_command
        call_command('ensure_contracts_report_module', verbosity=0)
