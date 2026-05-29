from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pos', '0009_client_predio_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='client',
            name='predio_registry_number',
            field=models.CharField(blank=True, max_length=50, null=True, verbose_name='Número de partida del predio'),
        ),
    ]
