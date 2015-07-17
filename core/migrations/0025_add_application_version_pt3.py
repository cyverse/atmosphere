# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.utils.timezone
from django.conf import settings
import uuid
import json

VERBOSE = False


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0024_add_application_version_pt2'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='applicationthreshold',
            name='application',
        ),
        migrations.RemoveField(
            model_name='machinerequest',
            name='new_machine_description',
        ),
        migrations.RemoveField(
            model_name='machinerequest',
            name='new_machine_name',
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
        migrations.RemoveField(
            model_name='providermachine',
            name='allow_imaging',
        ),
        migrations.RemoveField(
            model_name='providermachine',
            name='application',
        ),
        migrations.RemoveField(
            model_name='providermachine',
            name='licenses',
        ),
        migrations.RemoveField(
            model_name='providermachine',
            name='version',
        ),
    ]
