# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0050_unique_instance_action_and_help_link'),
    ]

    operations = [
        migrations.AlterField(
            model_name='instanceaction',
            name='key',
            field=models.CharField(unique=True, max_length=256),
        ),
    ]
