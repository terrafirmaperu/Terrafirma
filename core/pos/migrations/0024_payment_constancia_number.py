# -*- coding: utf-8 -*-
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pos', '0023_advisoryprogressstage_visible_portal'),
    ]

    operations = [
        migrations.CreateModel(
            name='PaymentConstanciaCounter',
            fields=[
                ('id', models.PositiveSmallIntegerField(default=1, editable=False, primary_key=True, serialize=False)),
                ('last_number', models.PositiveIntegerField(default=0, verbose_name='Último N° de constancia')),
            ],
            options={
                'verbose_name': 'Correlativo constancias de pago',
                'verbose_name_plural': 'Correlativo constancias de pago',
            },
        ),
        migrations.AddField(
            model_name='paymentsctacollect',
            name='constancia_number',
            field=models.PositiveIntegerField(
                blank=True,
                db_index=True,
                editable=False,
                null=True,
                unique=True,
                verbose_name='N° constancia de pago',
            ),
        ),
    ]
