from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pos', '0039_client_divorce_separation_docs'),
    ]

    operations = [
        migrations.AddField(
            model_name='sale',
            name='quota_plan_override',
            field=models.JSONField(
                blank=True,
                help_text='Cuotas editadas por administrador en cuentas por cobrar.',
                null=True,
                verbose_name='Plan de cuotas personalizado',
            ),
        ),
    ]
