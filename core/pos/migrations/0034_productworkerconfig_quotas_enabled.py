from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pos', '0033_productworkerconfig_inscription'),
    ]

    operations = [
        migrations.AddField(
            model_name='productworkerconfig',
            name='quotas_enabled',
            field=models.BooleanField(default=False, verbose_name='Cuotas habilitadas'),
        ),
    ]
