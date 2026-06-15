from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('pos', '0034_productworkerconfig_quotas_enabled'),
    ]

    operations = [
        migrations.AddField(
            model_name='paymentsctacollect',
            name='worker_deliverable',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='ctacollect_payments',
                to='pos.productworkerdeliverable',
                verbose_name='Entregable / proceso',
            ),
        ),
        migrations.AddField(
            model_name='paymentsctacollect',
            name='worker_inscription_product',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='worker_inscription_payments',
                to='pos.product',
                verbose_name='Inscripción (producto)',
            ),
        ),
    ]
