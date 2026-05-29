# -*- coding: utf-8 -*-
import django.core.validators
from django.db import migrations, models


def clamp_existing_stages(apps, schema_editor):
    AdvisoryProgressCase = apps.get_model('pos', 'AdvisoryProgressCase')
    for case in AdvisoryProgressCase.objects.all():
        changed = False
        if case.total_stages < 2:
            case.total_stages = 2
            changed = True
        if case.total_stages > 9:
            case.total_stages = 9
            changed = True
        if case.current_stage > case.total_stages:
            case.current_stage = case.total_stages
            changed = True
        if changed:
            case.save(update_fields=['total_stages', 'current_stage'])


class Migration(migrations.Migration):

    dependencies = [
        ('pos', '0014_advisory_progress'),
    ]

    operations = [
        migrations.AlterField(
            model_name='advisoryprogresscase',
            name='total_stages',
            field=models.PositiveSmallIntegerField(
                default=5,
                validators=[
                    django.core.validators.MinValueValidator(2),
                    django.core.validators.MaxValueValidator(9),
                ],
                verbose_name='Cantidad de etapas',
            ),
        ),
        migrations.AlterField(
            model_name='advisoryprogresscase',
            name='current_stage',
            field=models.PositiveSmallIntegerField(
                default=1,
                validators=[
                    django.core.validators.MinValueValidator(1),
                    django.core.validators.MaxValueValidator(9),
                ],
                verbose_name='Etapa actual',
            ),
        ),
        migrations.RunPython(clamp_existing_stages, migrations.RunPython.noop),
    ]
