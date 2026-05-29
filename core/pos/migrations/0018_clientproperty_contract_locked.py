# -*- coding: utf-8 -*-
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pos', '0017_clientproperty_product'),
    ]

    operations = [
        migrations.AddField(
            model_name='clientproperty',
            name='contract_locked_at',
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name='Contrato generado (bloqueo de desvinculación)',
            ),
        ),
    ]
