from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pos', '0029_collector_sale'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='collector',
            name='first_name',
        ),
        migrations.RemoveField(
            model_name='collector',
            name='last_name',
        ),
        migrations.AddField(
            model_name='collector',
            name='name',
            field=models.CharField(default='', max_length=200, unique=True, verbose_name='Nombre'),
            preserve_default=False,
        ),
        migrations.AlterModelOptions(
            name='collector',
            options={'ordering': ['name', 'id'], 'verbose_name': 'Cobrador', 'verbose_name_plural': 'Cobradores'},
        ),
    ]
