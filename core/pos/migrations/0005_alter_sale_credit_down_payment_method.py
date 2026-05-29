from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pos', '0004_sale_credit_down_payment_method'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sale',
            name='credit_down_payment_method',
            field=models.CharField(
                choices=[
                    ('efectivo', 'Efectivo'),
                    ('yape', 'Yape'),
                    ('plin', 'Plin'),
                    ('tarjeta_debito_credito', 'Tarjeta'),
                ],
                default='efectivo',
                max_length=50,
                verbose_name='Inicial pagada con',
            ),
        ),
    ]
