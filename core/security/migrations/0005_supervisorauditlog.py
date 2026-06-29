# Generated manually for supervisor audit log

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('security', '0004_alter_dniapiconfiguration_id'),
    ]

    operations = [
        migrations.CreateModel(
            name='SupervisorAuditLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Fecha y hora')),
                ('category', models.CharField(
                    choices=[('autorizacion', 'Autorización'), ('accion', 'Acción')],
                    default='accion',
                    max_length=20,
                )),
                ('event_type', models.CharField(max_length=60, verbose_name='Tipo')),
                ('summary', models.CharField(max_length=255, verbose_name='Resumen')),
                ('detail', models.TextField(blank=True, default='', verbose_name='Detalle')),
                ('ip_address', models.CharField(blank=True, default='', max_length=45)),
                ('request_path', models.CharField(blank=True, default='', max_length=500)),
                ('object_type', models.CharField(blank=True, default='', max_length=120)),
                ('object_id', models.CharField(blank=True, default='', max_length=80)),
                ('actor_user', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='supervisor_audit_actions',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='Usuario en sesión',
                )),
                ('supervisor_user', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='supervisor_audit_authorizations',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='Supervisor autorizó',
                )),
            ],
            options={
                'verbose_name': 'Registro supervisor',
                'verbose_name_plural': 'Registros supervisor',
                'ordering': ['-created_at', '-id'],
                'default_permissions': (),
            },
        ),
    ]
