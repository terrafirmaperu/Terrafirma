from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pos', '0003_sale_credit_quotas'),
    ]

    operations = [
        migrations.AddField(
            model_name='sale',
            name='credit_down_payment_method',
            field=models.CharField(
                choices=[('efectivo', 'Efectivo'), ('yape', 'Yape'), ('plin', 'Plin')],
                default='efectivo',
                max_length=50,
                verbose_name='Inicial pagada con',
            ),
        ),
    ]
