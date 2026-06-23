# Generated manually for estado civil en clientes

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pos', '0036_sale_payment_efectivo_yape'),
    ]

    operations = [
        migrations.AddField(
            model_name='client',
            name='marital_status',
            field=models.CharField(
                blank=True,
                choices=[
                    ('soltero', 'Soltero(a)'),
                    ('casado', 'Casado(a)'),
                    ('viudo', 'Viudo(a)'),
                    ('divorciado', 'Divorciado(a)'),
                    ('separado', 'Separado(a)'),
                    ('conviviente', 'Conviviente / Unión de hecho'),
                ],
                default='',
                max_length=20,
                verbose_name='Estado civil',
            ),
        ),
    ]
