# -*- coding: utf-8 -*-
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pos', '0025_saledetail_client_property'),
    ]

    operations = [
        migrations.AddField(
            model_name='paymentsctacollect',
            name='payment_method',
            field=models.CharField(
                choices=[
                    ('efectivo', 'Efectivo'),
                    ('yape', 'Yape'),
                    ('plin', 'Plin'),
                    ('tarjeta_debito_credito', 'Tarjeta'),
                ],
                default='efectivo',
                max_length=50,
                verbose_name='Forma de pago',
            ),
        ),
    ]
