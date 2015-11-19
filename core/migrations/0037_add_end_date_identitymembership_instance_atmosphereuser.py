# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0036_complete_the_uuid_merge'),
    ]

    operations = [
        migrations.AddField(
            model_name='atmosphereuser',
            name='end_date',
            field=models.DateTimeField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='identitymembership',
            name='end_date',
            field=models.DateTimeField(null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='instance',
            name='end_date',
            field=models.DateTimeField(null=True, blank=True),
        ),
    ]
