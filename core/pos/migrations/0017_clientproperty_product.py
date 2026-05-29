# -*- coding: utf-8 -*-
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('pos', '0016_client_property'),
    ]

    operations = [
        migrations.AddField(
            model_name='clientproperty',
            name='product',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='client_properties',
                to='pos.product',
                verbose_name='Producto / servicio a facturar',
            ),
        ),
    ]
