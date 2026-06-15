from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('pos', '0030_collector_single_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='paymentsctacollect',
            name='collector',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='payments',
                to='pos.collector',
                verbose_name='Lugar de cobro',
            ),
        ),
    ]
