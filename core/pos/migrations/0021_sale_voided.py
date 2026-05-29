# -*- coding: utf-8 -*-
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('pos', '0020_advisoryprogresscase_sale'),
    ]

    operations = [
        migrations.AddField(
            model_name='sale',
            name='is_voided',
            field=models.BooleanField(default=False, verbose_name='Anulada'),
        ),
        migrations.AddField(
            model_name='sale',
            name='voided_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Fecha de anulación'),
        ),
        migrations.AddField(
            model_name='sale',
            name='voided_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='voided_sales',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Anulada por',
            ),
        ),
    ]
