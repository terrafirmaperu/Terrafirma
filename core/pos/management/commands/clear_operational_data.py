"""
Elimina datos operativos de prueba/simulación y deja listo el arranque en producción.

Conserva: empresa, catálogo (categorías/productos), tipos de gasto, usuarios staff,
permisos y configuración de seguridad.

  python manage.py clear_operational_data
  python manage.py clear_operational_data --no-input
"""

from django.core.management.base import BaseCommand
from django.db import connection, transaction

from core.pos.models import (
    AdvisoryProgressCase,
    CashRegisterSession,
    Client,
    ClientCodeCounter,
    ClientProperty,
    CtasCollect,
    DebtsPay,
    Devolution,
    Expenses,
    PaymentConstanciaCounter,
    PaymentsCtaCollect,
    PaymentsDebtsPay,
    Promotions,
    PromotionsDetail,
    Purchase,
    PurchaseDetail,
    Sale,
    SaleDetail,
)
from core.user.models import User


class Command(BaseCommand):
    help = 'Borra ventas, cobros, clientes de simulación y datos operativos relacionados.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--no-input',
            action='store_true',
            help='No pedir confirmación.',
        )

    def handle(self, *args, **options):
        if not options['no_input']:
            confirm = input(
                'Se borrarán ventas, pagos, cuentas por cobrar, clientes y casos de asesoría. '
                '¿Continuar? [s/N]: '
            )
            if (confirm or '').strip().lower() not in ('s', 'si', 'sí', 'y', 'yes'):
                self.stdout.write('Cancelado.')
                return

        client_user_ids = list(
            Client.objects.values_list('user_id', flat=True).distinct()
        )

        with transaction.atomic():
            deleted = {}
            deleted['devolution'] = Devolution.objects.all().delete()[0]
            deleted['payments_ctacollect'] = PaymentsCtaCollect.objects.all().delete()[0]
            deleted['ctascollect'] = CtasCollect.objects.all().delete()[0]
            deleted['payments_debtspay'] = PaymentsDebtsPay.objects.all().delete()[0]
            deleted['debtspay'] = DebtsPay.objects.all().delete()[0]
            deleted['advisory_case'] = AdvisoryProgressCase.objects.all().delete()[0]
            deleted['sale_detail'] = SaleDetail.objects.all().delete()[0]
            deleted['sale'] = Sale.objects.all().delete()[0]
            deleted['purchase_detail'] = PurchaseDetail.objects.all().delete()[0]
            deleted['purchase'] = Purchase.objects.all().delete()[0]
            deleted['expenses'] = Expenses.objects.all().delete()[0]
            deleted['promotions_detail'] = PromotionsDetail.objects.all().delete()[0]
            deleted['promotions'] = Promotions.objects.all().delete()[0]
            deleted['cash_session'] = CashRegisterSession.objects.all().delete()[0]
            deleted['client_property'] = ClientProperty.objects.all().delete()[0]
            deleted['client'] = Client.objects.all().delete()[0]

            users_removed = 0
            if client_user_ids:
                qs = User.objects.filter(pk__in=client_user_ids).filter(
                    is_staff=False,
                    is_superuser=False,
                )
                users_removed = qs.count()
                qs.delete()

            ClientCodeCounter.objects.update_or_create(pk=1, defaults={'last_seq': 0})
            PaymentConstanciaCounter.objects.update_or_create(pk=1, defaults={'last_number': 0})

        self._reset_sqlite_sequences()

        self.stdout.write(self.style.SUCCESS('Datos operativos eliminados.'))
        for key, count in deleted.items():
            if count:
                self.stdout.write('  · {}: {}'.format(key, count))
        if users_removed:
            self.stdout.write('  · usuarios cliente: {}'.format(users_removed))
        self.stdout.write('Contadores de código cliente y constancia reiniciados.')

    def _reset_sqlite_sequences(self):
        if connection.vendor != 'sqlite':
            return
        tables = [
            'pos_devolution',
            'pos_paymentsctacollect',
            'pos_ctascollect',
            'pos_paymentsdebtspay',
            'pos_debtspay',
            'pos_saledetail',
            'pos_sale',
            'pos_purchasedetail',
            'pos_purchase',
            'pos_expenses',
            'pos_promotionsdetail',
            'pos_promotions',
            'pos_cashregistersession',
            'pos_advisoryprogressstage',
            'pos_advisoryprogresscase',
            'pos_clientproperty',
            'pos_client',
        ]
        with connection.cursor() as cursor:
            for table in tables:
                cursor.execute(
                    "DELETE FROM sqlite_sequence WHERE name = %s",
                    [table],
                )
