"""Anulación de ventas (no borrado físico)."""

from django.db import transaction
from django.utils import timezone


class SaleAlreadyVoidedError(ValueError):
    pass


def annul_sale(sale, user=None):
    """
    Anula una venta: elimina cuenta por cobrar asociada, oculta asesoría en portal
    y marca la venta como anulada.
    """
    if not sale or not sale.pk:
        raise ValueError('Venta no válida.')
    if getattr(sale, 'is_voided', False):
        raise SaleAlreadyVoidedError('Esta venta ya está anulada.')

    from core.pos.client_properties import unlock_client_properties_for_sale
    from core.pos.models import AdvisoryProgressCase, CtasCollect

    with transaction.atomic():
        for cta in CtasCollect.objects.filter(sale_id=sale.pk):
            cta.paymentsctacollect_set.all().delete()
            cta.delete()

        AdvisoryProgressCase.objects.filter(sale_id=sale.pk).update(is_visible_portal=False)
        unlock_client_properties_for_sale(sale)

        sale.is_voided = True
        sale.voided_at = timezone.now()
        sale.voided_by = user
        sale.save(update_fields=['is_voided', 'voided_at', 'voided_by'])

    return sale
