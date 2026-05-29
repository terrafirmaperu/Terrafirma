from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pos', '0008_client_location_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='client',
            name='has_predio',
            field=models.BooleanField(default=False, verbose_name='Vincular a predio'),
        ),
        migrations.AddField(
            model_name='client',
            name='predio_address',
            field=models.CharField(blank=True, max_length=500, null=True, verbose_name='Dirección del predio'),
        ),
        migrations.AddField(
            model_name='client',
            name='predio_area',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True, verbose_name='Área aproximada'),
        ),
        migrations.AddField(
            model_name='client',
            name='predio_block',
            field=models.CharField(blank=True, max_length=30, null=True, verbose_name='Manzana'),
        ),
        migrations.AddField(
            model_name='client',
            name='predio_department',
            field=models.CharField(blank=True, max_length=80, null=True, verbose_name='Departamento del predio'),
        ),
        migrations.AddField(
            model_name='client',
            name='predio_district',
            field=models.CharField(blank=True, max_length=80, null=True, verbose_name='Distrito del predio'),
        ),
        migrations.AddField(
            model_name='client',
            name='predio_lot_number',
            field=models.CharField(blank=True, max_length=30, null=True, verbose_name='Número de lote'),
        ),
        migrations.AddField(
            model_name='client',
            name='predio_perimeter',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True, verbose_name='Perímetro'),
        ),
        migrations.AddField(
            model_name='client',
            name='predio_province',
            field=models.CharField(blank=True, max_length=80, null=True, verbose_name='Provincia del predio'),
        ),
        migrations.AddField(
            model_name='client',
            name='predio_type',
            field=models.CharField(blank=True, choices=[('terreno', 'Terreno'), ('casa', 'Casa'), ('departamento', 'Departamento'), ('local_comercial', 'Local comercial'), ('otros', 'Otros')], max_length=30, null=True, verbose_name='Tipo de predio'),
        ),
    ]
