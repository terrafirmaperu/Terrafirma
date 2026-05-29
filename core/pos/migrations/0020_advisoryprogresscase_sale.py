# -*- coding: utf-8 -*-
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('pos', '0019_clientproperty_unlock_perm'),
    ]

    operations = [
        migrations.AddField(
            model_name='advisoryprogresscase',
            name='sale',
            field=models.OneToOneField(
                blank=True,
                help_text='Cada contrata generada crea un caso vinculado a la venta.',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='advisory_case',
                to='pos.sale',
                verbose_name='Venta / contrata',
            ),
        ),
    ]
