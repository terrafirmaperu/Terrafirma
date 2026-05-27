# -*- coding: utf-8 -*-
"""Actualiza datos de Empresa para constancias de pago y documentos."""
from django.core.management.base import BaseCommand

from core.pos.models import Company
from core.pos.views.frm.ctascollect.payment_constancia import CONSTANCIA_COMPANY_DEFAULTS


class Command(BaseCommand):
    help = 'Sincroniza la ficha Empresa con los datos legales de TERRAFIRMA para constancias.'

    def handle(self, *args, **options):
        company = Company.objects.first()
        if not company:
            company = Company()
        company.name = CONSTANCIA_COMPANY_DEFAULTS['legal_name']
        company.ruc = CONSTANCIA_COMPANY_DEFAULTS['ruc']
        company.address = CONSTANCIA_COMPANY_DEFAULTS['address']
        company.mobile = CONSTANCIA_COMPANY_DEFAULTS['mobile']
        if not (company.website or '').strip():
            company.website = CONSTANCIA_COMPANY_DEFAULTS['website']
        company.save()
        self.stdout.write(self.style.SUCCESS(
            'Empresa actualizada: {} | RUC {}'.format(company.name, company.ruc)
        ))
