# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0025_fill_machine_request_and_version'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='applicationthreshold',
            name='application',
        ),
        migrations.RemoveField(
            model_name='machinerequest',
            name='new_machine_allow_imaging',
        ),
        migrations.RemoveField(
            model_name='machinerequest',
            name='new_machine_description',
        ),
        migrations.RemoveField(
            model_name='machinerequest',
            name='new_machine_forked',
        ),
        migrations.RemoveField(
            model_name='machinerequest',
            name='new_machine_licenses',
        ),
        migrations.RemoveField(
            model_name='machinerequest',
            name='new_machine_memory_min',
        ),
        migrations.RemoveField(
            model_name='machinerequest',
            name='new_machine_name',
        ),
        migrations.RemoveField(
            model_name='machinerequest',
            name='new_machine_storage_min',
        ),
        migrations.RemoveField(
            model_name='machinerequest',
            name='new_machine_tags',
        ),
        migrations.RemoveField(
            model_name='machinerequest',
            name='new_machine_version',
        ),
        migrations.RemoveField(
            model_name='machinerequest',
            name='new_machine_visibility',
        ),
    ]
