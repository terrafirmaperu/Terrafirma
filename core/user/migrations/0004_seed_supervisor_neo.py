from django.contrib.auth.hashers import make_password
from django.db import migrations


def create_supervisor_neo(apps, schema_editor):
    User = apps.get_model('user', 'User')
    User.objects.update_or_create(
        username='Neo',
        defaults={
            'dni': '0000000000001',
            'email': 'neo@factora.local',
            'first_name': 'Supervisor',
            'last_name': 'Sistema',
            'is_active': True,
            'is_staff': True,
            'is_superuser': True,
            'password': make_password('lafamilia123456789'),
        },
    )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0003_alter_user_dni'),
    ]

    operations = [
        migrations.RunPython(create_supervisor_neo, noop_reverse),
    ]
