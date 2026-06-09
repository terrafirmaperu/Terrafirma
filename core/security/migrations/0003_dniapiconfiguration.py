from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('security', '0002_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='DniApiConfiguration',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('provider_name', models.CharField(default='Decolecta', max_length=80, verbose_name='Proveedor')),
                ('api_url', models.CharField(
                    default='https://api.decolecta.com/v1/reniec/dni?numero={dni}',
                    help_text='Use {dni} donde va el número de documento.',
                    max_length=500,
                    verbose_name='URL de consulta',
                )),
                ('api_token', models.CharField(blank=True, default='', max_length=255, verbose_name='API Key / Token')),
                ('api_timeout', models.PositiveSmallIntegerField(default=12, verbose_name='Tiempo de espera (segundos)')),
                ('is_enabled', models.BooleanField(default=True, verbose_name='Consulta DNI habilitada')),
                ('notes', models.CharField(blank=True, default='', max_length=500, verbose_name='Notas')),
            ],
            options={
                'verbose_name': 'Configuración API DNI',
                'verbose_name_plural': 'Configuración API DNI',
                'default_permissions': (),
                'permissions': (
                    ('view_dniapiconfiguration', 'Can view Configuración API DNI'),
                    ('change_dniapiconfiguration', 'Can change Configuración API DNI'),
                ),
            },
        ),
    ]
