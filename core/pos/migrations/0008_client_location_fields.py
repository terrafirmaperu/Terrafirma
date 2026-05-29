from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pos', '0007_merge_20260509_0048'),
    ]

    operations = [
        migrations.AddField(
            model_name='client',
            name='department',
            field=models.CharField(blank=True, max_length=80, null=True, verbose_name='Departamento'),
        ),
        migrations.AddField(
            model_name='client',
            name='district',
            field=models.CharField(blank=True, max_length=80, null=True, verbose_name='Distrito'),
        ),
        migrations.AddField(
            model_name='client',
            name='province',
            field=models.CharField(blank=True, max_length=80, null=True, verbose_name='Provincia'),
        ),
    ]
