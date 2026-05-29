# -*- coding: utf-8 -*-
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pos', '0021_sale_voided'),
    ]

    operations = [
        migrations.AddField(
            model_name='clientproperty',
            name='community_location_enabled',
            field=models.BooleanField(
                default=False,
                verbose_name='Registrar comunidad / centro poblado',
            ),
        ),
        migrations.AddField(
            model_name='clientproperty',
            name='community',
            field=models.CharField(blank=True, max_length=120, verbose_name='Comunidad'),
        ),
        migrations.AddField(
            model_name='clientproperty',
            name='population_center',
            field=models.CharField(blank=True, max_length=200, verbose_name='Centro poblado'),
        ),
    ]
