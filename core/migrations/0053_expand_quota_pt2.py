# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0052_expand_quota'),
    ]

    operations = [
        # migrations.AlterUniqueTogether(
        #     name='quota',
        #     unique_together=set([('cpu', 'memory', 'storage', 'floating_ip_count', 'port_count', 'instance_count', 'snapshot_count', 'storage_count')]),
        # ),
        # migrations.RemoveField(
        #     model_name='quota',
        #     name='suspended_count',
        # ),
    ]
