# -*- coding: utf-8 -*-
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pos', '0022_clientproperty_community_location'),
    ]

    operations = [
        migrations.AddField(
            model_name='advisoryprogressstage',
            name='is_visible_portal',
            field=models.BooleanField(
                default=True,
                verbose_name='Visible en portal cliente',
            ),
        ),
    ]
