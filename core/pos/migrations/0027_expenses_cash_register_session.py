import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pos', '0026_paymentsctacollect_payment_method'),
    ]

    operations = [
        migrations.AddField(
            model_name='expenses',
            name='cash_register_session',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='expenses',
                to='pos.cashregistersession',
                verbose_name='Sesión de caja',
            ),
        ),
    ]
