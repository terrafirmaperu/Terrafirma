# -*- coding: utf-8 -*-
from django.db import migrations, models
import django.db.models.deletion


def copy_legacy_predios(apps, schema_editor):
    Client = apps.get_model('pos', 'Client')
    ClientProperty = apps.get_model('pos', 'ClientProperty')
    for client in Client.objects.filter(has_predio=True):
        if ClientProperty.objects.filter(client_id=client.pk).exists():
            continue
        ClientProperty.objects.create(
            client_id=client.pk,
            department=client.predio_department or '',
            province=client.predio_province or '',
            district=client.predio_district or '',
            address=client.predio_address or '',
            area=client.predio_area,
            perimeter=client.predio_perimeter,
            lot_number=client.predio_lot_number or '',
            block=client.predio_block or '',
            registry_number=client.predio_registry_number or '',
            predio_type=client.predio_type,
            is_primary=True,
            order=0,
        )


class Migration(migrations.Migration):

    dependencies = [
        ('pos', '0015_advisory_stage_limits'),
    ]

    operations = [
        migrations.CreateModel(
            name='ClientProperty',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('label', models.CharField(blank=True, max_length=120, verbose_name='Nombre / referencia')),
                ('department', models.CharField(blank=True, max_length=80, verbose_name='Departamento')),
                ('province', models.CharField(blank=True, max_length=80, verbose_name='Provincia')),
                ('district', models.CharField(blank=True, max_length=80, verbose_name='Distrito')),
                ('address', models.CharField(blank=True, max_length=500, verbose_name='Dirección')),
                ('area', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True, verbose_name='Área aproximada')),
                ('perimeter', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True, verbose_name='Perímetro')),
                ('lot_number', models.CharField(blank=True, max_length=30, verbose_name='Número de lote')),
                ('block', models.CharField(blank=True, max_length=30, verbose_name='Manzana')),
                ('registry_number', models.CharField(blank=True, max_length=50, verbose_name='Número de partida')),
                ('predio_type', models.CharField(blank=True, choices=[('terreno', 'Terreno'), ('casa', 'Casa'), ('departamento', 'Departamento'), ('local_comercial', 'Local comercial'), ('otros', 'Otros')], max_length=30, null=True, verbose_name='Tipo de predio')),
                ('is_primary', models.BooleanField(default=False, verbose_name='Predio principal')),
                ('order', models.PositiveSmallIntegerField(default=0, verbose_name='Orden')),
                ('client', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='properties', to='pos.client', verbose_name='Cliente')),
            ],
            options={
                'verbose_name': 'Predio del cliente',
                'verbose_name_plural': 'Predios del cliente',
                'ordering': ['order', 'id'],
            },
        ),
        migrations.RunPython(copy_legacy_predios, migrations.RunPython.noop),
    ]
