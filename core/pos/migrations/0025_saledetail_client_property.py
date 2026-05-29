# -*- coding: utf-8 -*-
import django.db.models.deletion
from django.db import migrations, models


def link_legacy_sale_details_to_properties(apps, schema_editor):
    ClientProperty = apps.get_model('pos', 'ClientProperty')
    SaleDetail = apps.get_model('pos', 'SaleDetail')

    for det in SaleDetail.objects.filter(client_property__isnull=True).select_related('sale'):
        if not det.sale_id or det.sale.is_voided:
            continue
        props = list(
            ClientProperty.objects.filter(
                client_id=det.sale.client_id,
                product_id=det.product_id,
            ).order_by('order', 'id')
        )
        if len(props) == 1:
            det.client_property_id = props[0].pk
            det.save(update_fields=['client_property_id'])
            continue
        locked = [p for p in props if p.contract_locked_at]
        if len(locked) == 1:
            det.client_property_id = locked[0].pk
            det.save(update_fields=['client_property_id'])
            continue
        if props:
            det.client_property_id = props[0].pk
            det.save(update_fields=['client_property_id'])


class Migration(migrations.Migration):

    dependencies = [
        ('pos', '0024_payment_constancia_number'),
    ]

    operations = [
        migrations.AddField(
            model_name='saledetail',
            name='client_property',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='sale_details',
                to='pos.clientproperty',
                verbose_name='Predio vinculado',
            ),
        ),
        migrations.RunPython(link_legacy_sale_details_to_properties, migrations.RunPython.noop),
    ]
