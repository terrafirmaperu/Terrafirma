from django.db import migrations, models


def forwards_rename_efectivo_tarjeta(apps, schema_editor):
    Sale = apps.get_model('pos', 'Sale')
    Sale.objects.filter(payment_method='efectivo_tarjeta').update(payment_method='efectivo_yape')


def backwards_rename_efectivo_yape(apps, schema_editor):
    Sale = apps.get_model('pos', 'Sale')
    Sale.objects.filter(payment_method='efectivo_yape').update(payment_method='efectivo_tarjeta')


class Migration(migrations.Migration):

    dependencies = [
        ('pos', '0035_paymentsctacollect_worker_entregable'),
    ]

    operations = [
        migrations.RunPython(forwards_rename_efectivo_tarjeta, backwards_rename_efectivo_yape),
        migrations.AlterField(
            model_name='sale',
            name='payment_method',
            field=models.CharField(
                choices=[
                    ('efectivo', 'Efectivo'),
                    ('yape', 'Yape'),
                    ('plin', 'Plin'),
                    ('tarjeta_debito_credito', 'Tarjeta'),
                    ('efectivo_yape', 'Efectivo / Yape'),
                ],
                default='efectivo',
                max_length=50,
            ),
        ),
    ]
