from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pos', '0038_client_marital_documents'),
    ]

    operations = [
        migrations.AddField(
            model_name='client',
            name='divorce_certificate',
            field=models.FileField(
                blank=True,
                null=True,
                upload_to='client/divorce/%Y/%m/',
                verbose_name='Documento de divorcio',
            ),
        ),
        migrations.AddField(
            model_name='client',
            name='separation_certificate',
            field=models.FileField(
                blank=True,
                null=True,
                upload_to='client/separation/%Y/%m/',
                verbose_name='Documento de separación',
            ),
        ),
    ]
