# -*- coding: utf-8 -*-
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('pos', '0013_client_code_initials_counter'),
    ]

    operations = [
        migrations.CreateModel(
            name='AdvisoryProgressCase',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200, verbose_name='Terreno / caso')),
                ('predio_summary', models.CharField(blank=True, help_text='Opcional. Se puede completar desde los datos del predio del cliente.', max_length=500, verbose_name='Resumen ubicación')),
                ('total_stages', models.PositiveSmallIntegerField(default=5, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(12)], verbose_name='Cantidad de etapas')),
                ('current_stage', models.PositiveSmallIntegerField(default=1, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(12)], verbose_name='Etapa actual')),
                ('is_visible_portal', models.BooleanField(default=True, verbose_name='Visible en portal cliente')),
                ('notes', models.TextField(blank=True, verbose_name='Notas internas')),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('client', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='advisory_cases', to='pos.client', verbose_name='Cliente')),
            ],
            options={
                'verbose_name': 'Control de avance asesoría',
                'verbose_name_plural': 'Control de avance asesoría',
                'ordering': ['-updated_at', '-id'],
                'permissions': (
                    ('view_advisoryprogresscase', 'Can view Control de avance asesoría'),
                    ('add_advisoryprogresscase', 'Can add Control de avance asesoría'),
                    ('change_advisoryprogresscase', 'Can change Control de avance asesoría'),
                    ('delete_advisoryprogresscase', 'Can delete Control de avance asesoría'),
                ),
                'default_permissions': (),
            },
        ),
        migrations.CreateModel(
            name='AdvisoryProgressStage',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('order', models.PositiveSmallIntegerField(verbose_name='Orden')),
                ('title', models.CharField(max_length=150, verbose_name='Título de etapa')),
                ('description', models.TextField(blank=True, verbose_name='Descripción')),
                ('case', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='stages', to='pos.advisoryprogresscase', verbose_name='Caso')),
            ],
            options={
                'verbose_name': 'Etapa de avance',
                'verbose_name_plural': 'Etapas de avance',
                'ordering': ['order'],
                'unique_together': {('case', 'order')},
            },
        ),
    ]
