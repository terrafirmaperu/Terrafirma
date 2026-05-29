# Generated manually

from django.db import migrations, models


def populate_codes(apps, schema_editor):
    Client = apps.get_model('pos', 'Client')
    for c in Client.objects.all().order_by('id'):
        Client.objects.filter(pk=c.pk).update(client_code='CL-{:06d}'.format(c.id))
    Sale = apps.get_model('pos', 'Sale')
    for s in Sale.objects.all().order_by('id'):
        Sale.objects.filter(pk=s.pk).update(
            sale_code='VT-{:06d}'.format(s.id),
            contract_code='CT-{:06d}'.format(s.id),
        )


class Migration(migrations.Migration):

    dependencies = [
        ('pos', '0011_search_performance_indexes'),
    ]

    operations = [
        migrations.AddField(
            model_name='client',
            name='client_code',
            field=models.CharField(
                blank=True,
                editable=False,
                help_text='Identificador único interno (CL-######), asignado al guardar.',
                max_length=20,
                null=True,
                unique=True,
                verbose_name='Código de cliente',
            ),
        ),
        migrations.AddField(
            model_name='sale',
            name='sale_code',
            field=models.CharField(
                blank=True,
                editable=False,
                help_text='Identificador único interno (VT-######), asignado al guardar.',
                max_length=20,
                null=True,
                unique=True,
                verbose_name='Código de venta',
            ),
        ),
        migrations.AddField(
            model_name='sale',
            name='contract_code',
            field=models.CharField(
                blank=True,
                editable=False,
                help_text='Un contrato por venta (CT-######), asignado al guardar.',
                max_length=20,
                null=True,
                unique=True,
                verbose_name='Código de contrato',
            ),
        ),
        migrations.RunPython(populate_codes, migrations.RunPython.noop),
    ]
