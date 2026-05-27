# -*- coding: utf-8 -*-
"""
Quita bloqueos de contrata en predios que no corresponden a su producto/venta.

  python manage.py repair_predio_contract_locks
  python manage.py repair_predio_contract_locks --client-id 5
"""

from django.core.management.base import BaseCommand

from core.pos.client_properties import repair_client_property_contract_locks
from core.pos.models import Client


class Command(BaseCommand):
    help = 'Corrige predios bloqueados por contrata de otro predio del mismo cliente.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--client-id',
            type=int,
            default=None,
            help='Solo revisar un cliente (opcional).',
        )

    def handle(self, *args, **options):
        client_id = options.get('client_id')
        if client_id and not Client.objects.filter(pk=client_id).exists():
            self.stdout.write(self.style.ERROR('Cliente {} no existe.'.format(client_id)))
            return
        fixed = repair_client_property_contract_locks(client_id=client_id)
        self.stdout.write(
            self.style.SUCCESS(
                'Predios corregidos: {}.'.format(fixed)
            )
        )
