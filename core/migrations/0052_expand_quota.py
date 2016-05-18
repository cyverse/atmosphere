# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import core.models.quota


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0051_non_null_key_instance_action'),
    ]

    operations = [
        migrations.AddField(
            model_name='quota',
            name='floating_ip_count',
            field=models.IntegerField(default=core.models.quota._get_default_floating_ip_count, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='quota',
            name='instance_count',
            field=models.IntegerField(default=core.models.quota._get_default_instance_count, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='quota',
            name='port_count',
            field=models.IntegerField(default=core.models.quota._get_default_port_count, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='quota',
            name='snapshot_count',
            field=models.IntegerField(default=core.models.quota._get_default_snapshot_count, null=True, blank=True),
        ),
        migrations.AlterUniqueTogether(
            name='quota',
            unique_together=set([]),
        ),
    ]
