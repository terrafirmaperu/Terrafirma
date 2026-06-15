from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('pos', '0031_paymentsctacollect_collector'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProductWorkerConfig',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quota_count', models.PositiveSmallIntegerField(default=1, verbose_name='Número de cuotas')),
                ('quota_amount', models.DecimalField(decimal_places=2, default=0.0, max_digits=9, verbose_name='Monto por cuota')),
                ('product', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='worker_config', to='pos.product', verbose_name='Producto')),
            ],
            options={
                'verbose_name': 'Configuración obrero (producto)',
                'verbose_name_plural': 'Configuraciones obrero (producto)',
            },
        ),
        migrations.CreateModel(
            name='ProductWorkerDeliverable',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('order', models.PositiveSmallIntegerField(default=1, verbose_name='Orden')),
                ('name', models.CharField(max_length=200, verbose_name='Entregable / proceso')),
                ('charge_amount', models.DecimalField(decimal_places=2, default=0.0, max_digits=9, verbose_name='Cobro')),
                ('notes', models.CharField(blank=True, default='', max_length=300, verbose_name='Notas')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='worker_deliverables', to='pos.product', verbose_name='Producto')),
            ],
            options={
                'verbose_name': 'Entregable obrero',
                'verbose_name_plural': 'Entregables obrero',
                'ordering': ['order', 'id'],
            },
        ),
        migrations.AddIndex(
            model_name='productworkerdeliverable',
            index=models.Index(fields=['product', 'order'], name='pos_worker_deliv_prod_ord'),
        ),
    ]
