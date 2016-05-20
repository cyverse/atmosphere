# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import core.models.allocation_strategy


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0043_meta_update_project_links_and_machinerequest_new_version_membership'),
    ]

    operations = [
        migrations.AlterField(
            model_name='allocation',
            name='delta',
            field=models.IntegerField(default=core.models.allocation_strategy._get_default_delta, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='allocation',
            name='threshold',
            field=models.IntegerField(default=core.models.allocation_strategy._get_default_threshold, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='quota',
            name='cpu',
            field=models.IntegerField(default=core.models.quota._get_default_cpu, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='quota',
            name='memory',
            field=models.IntegerField(default=core.models.quota._get_default_memory, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='quota',
            name='storage',
            field=models.IntegerField(default=core.models.quota._get_default_storage, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='quota',
            name='storage_count',
            field=models.IntegerField(default=core.models.quota._get_default_storage_count, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='quota',
            name='suspended_count',
            field=models.IntegerField(default=-1, null=True, blank=True),
        ),
    ]
