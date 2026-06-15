from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pos', '0032_product_worker'),
    ]

    operations = [
        migrations.AddField(
            model_name='productworkerconfig',
            name='inscription_amount',
            field=models.DecimalField(decimal_places=2, default=0.0, max_digits=9, verbose_name='Inscripción'),
        ),
    ]
