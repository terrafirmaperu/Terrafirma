"""Regenera etapas faltantes en todos los casos de avance."""

from django.core.management.base import BaseCommand

from core.pos.models import AdvisoryProgressCase, sync_advisory_progress_stages


class Command(BaseCommand):
    help = 'Sincroniza etapas (AdvisoryProgressStage) para cada caso existente.'

    def handle(self, *args, **options):
        count = 0
        for case in AdvisoryProgressCase.objects.all():
            before = case.stages.count()
            sync_advisory_progress_stages(case)
            after = case.stages.count()
            count += 1
            self.stdout.write(f'Caso {case.id}: {before} -> {after} etapas')
        self.stdout.write(self.style.SUCCESS(f'Procesados {count} caso(s).'))
