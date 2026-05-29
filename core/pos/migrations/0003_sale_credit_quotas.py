import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pos', '0002_cashregistersession'),
    ]

    operations = [
        migrations.AddField(
            model_name='sale',
            name='credit_down_payment',
            field=models.DecimalField(decimal_places=2, default=0.0, max_digits=9, verbose_name='Inicial'),
        ),
        migrations.AddField(
            model_name='sale',
            name='credit_quota_count',
            field=models.PositiveSmallIntegerField(
                default=1,
                help_text='Cuotas programadas (1 a 5), sin contar el pago inicial.',
                validators=[
                    django.core.validators.MinValueValidator(1),
                    django.core.validators.MaxValueValidator(5),
                ],
                verbose_name='Número de cuotas',
            ),
        ),
    ]
