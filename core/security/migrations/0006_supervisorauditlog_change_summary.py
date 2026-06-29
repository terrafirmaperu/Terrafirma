# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('security', '0005_supervisorauditlog'),
    ]

    operations = [
        migrations.AddField(
            model_name='supervisorauditlog',
            name='change_summary',
            field=models.TextField(blank=True, default='', verbose_name='Cambio realizado'),
        ),
    ]
