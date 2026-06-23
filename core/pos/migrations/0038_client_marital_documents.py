from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pos', '0037_client_marital_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='client',
            name='spouse_first_name',
            field=models.CharField(
                blank=True, default='', max_length=150, verbose_name='Nombres del cónyuge',
            ),
        ),
        migrations.AddField(
            model_name='client',
            name='spouse_last_name',
            field=models.CharField(
                blank=True, default='', max_length=150, verbose_name='Apellidos del cónyuge',
            ),
        ),
        migrations.AddField(
            model_name='client',
            name='spouse_dni',
            field=models.CharField(
                blank=True, default='', max_length=12, verbose_name='DNI del cónyuge',
            ),
        ),
        migrations.AddField(
            model_name='client',
            name='marriage_certificate',
            field=models.FileField(
                blank=True,
                null=True,
                upload_to='client/marriage/%Y/%m/',
                verbose_name='Acta de matrimonio',
            ),
        ),
        migrations.AddField(
            model_name='client',
            name='death_certificate',
            field=models.FileField(
                blank=True,
                null=True,
                upload_to='client/death/%Y/%m/',
                verbose_name='Acta de defunción',
            ),
        ),
    ]
