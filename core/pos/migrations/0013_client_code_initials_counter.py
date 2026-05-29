# -*- coding: utf-8 -*-
import unicodedata

from django.db import migrations, models


def _initial(text):
    if not text or not str(text).strip():
        return 'X'
    ch = unicodedata.normalize('NFD', str(text).strip()[0])[0]
    if not ch.isalpha():
        return 'X'
    return ch.upper()


def rebuild_client_codes_and_counter(apps, schema_editor):
    Client = apps.get_model('pos', 'Client')
    User = apps.get_model('user', 'User')
    ClientCodeCounter = apps.get_model('pos', 'ClientCodeCounter')

    seq = 0
    for c in Client.objects.all().order_by('id'):
        user = User.objects.get(pk=c.user_id)
        dept = (c.department or c.predio_department or '').strip()
        d = _initial(dept)
        n = _initial((user.first_name or '').strip())
        ln = (user.last_name or '').strip()
        paternal = ln.split()[0] if ln else ''
        p = _initial(paternal)
        prefix = '{}{}{}'.format(d, n, p)
        seq += 1
        code = '{}{:05d}'.format(prefix, seq)
        Client.objects.filter(pk=c.pk).update(client_code=code)

    ClientCodeCounter.objects.update_or_create(
        pk=1,
        defaults={'last_seq': seq},
    )


class Migration(migrations.Migration):

    dependencies = [
        ('pos', '0012_client_sale_contract_codes'),
    ]

    operations = [
        migrations.CreateModel(
            name='ClientCodeCounter',
            fields=[
                ('id', models.PositiveSmallIntegerField(default=1, primary_key=True, serialize=False)),
                ('last_seq', models.PositiveIntegerField(default=0, verbose_name='Último correlativo')),
            ],
            options={
                'verbose_name': 'Contador código de cliente',
                'verbose_name_plural': 'Contador códigos de cliente',
            },
        ),
        migrations.AlterField(
            model_name='client',
            name='client_code',
            field=models.CharField(
                blank=True,
                editable=False,
                help_text='Letras (depto + nombre + apellido paterno) + 5 cifras correlativas. No se modifica tras asignar.',
                max_length=20,
                null=True,
                unique=True,
                verbose_name='Código de cliente',
            ),
        ),
        migrations.RunPython(rebuild_client_codes_and_counter, migrations.RunPython.noop),
    ]
