# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0048_providerconfiguration'),
    ]

    operations = [
        migrations.AddField(
            model_name='instancestatushistory',
            name='activity',
            field=models.CharField(max_length=36, null=True, blank=True),
        ),
    ]
