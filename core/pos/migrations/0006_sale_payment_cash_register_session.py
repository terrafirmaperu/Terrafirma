import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pos', '0005_alter_sale_credit_down_payment_method'),
    ]

    operations = [
        migrations.AddField(
            model_name='sale',
            name='cash_register_session',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='sales',
                to='pos.cashregistersession',
                verbose_name='Sesión de caja',
            ),
        ),
        migrations.AddField(
            model_name='paymentsctacollect',
            name='cash_register_session',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='payments_ctacollect',
                to='pos.cashregistersession',
                verbose_name='Sesión de caja',
            ),
        ),
    ]
