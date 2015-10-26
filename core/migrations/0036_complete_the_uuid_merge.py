# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0035_uuid_unique_all_the_things'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='application',
            name='uuid',
        ),
        migrations.RemoveField(
            model_name='cloudadministrator',
            name='uuid',
        ),
        migrations.RemoveField(
            model_name='machinerequest',
            name='uuid',
        ),
        migrations.RemoveField(
            model_name='project',
            name='uuid',
        ),
        migrations.RemoveField(
            model_name='identity',
            name='uuid',
        ),
        migrations.RemoveField(
            model_name='provider',
            name='uuid',
        ),
        migrations.RemoveField(
            model_name='resourcerequest',
            name='uuid',
        ),
        migrations.RenameField(
           'application', 'uuid2', 'uuid'
        ),
        migrations.RenameField(
            'cloudadministrator', 'uuid2', 'uuid'
        ),
        migrations.RenameField(
            'identity', 'uuid2', 'uuid'
        ),
        migrations.AlterField(
            model_name='applicationversion',
            name='id',
            field=models.UUIDField(primary_key=True, default=uuid.uuid4, serialize=False, editable=False, unique=True),
        ),
        migrations.RenameField(
            'machinerequest', 'uuid2', 'uuid'
        ),
        migrations.RenameField(
            'project', 'uuid2', 'uuid'
        ),
        migrations.RenameField(
            'provider', 'uuid2', 'uuid'
        ),
        migrations.RenameField(
            'resourcerequest', 'uuid2', 'uuid'
        ),
    ]
