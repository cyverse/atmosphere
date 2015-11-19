# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0032_alter_machine_request'),
    ]

    operations = [
        migrations.AddField(
            model_name='application',
            name='uuid2',
            field=models.UUIDField(null=True),
        ),
        migrations.AddField(
            model_name='cloudadministrator',
            name='uuid2',
            field=models.UUIDField(null=True),
        ),
        migrations.AddField(
            model_name='identity',
            name='uuid2',
            field=models.UUIDField(null=True),
        ),
        migrations.AddField(
            model_name='machinerequest',
            name='uuid2',
            field=models.UUIDField(null=True),
        ),
        migrations.AddField(
            model_name='project',
            name='uuid2',
            field=models.UUIDField(null=True),
        ),
        migrations.AddField(
            model_name='provider',
            name='uuid2',
            field=models.UUIDField(null=True),
        ),
        ######################################
        migrations.AddField(
            model_name='allocation',
            name='uuid',
            field=models.UUIDField(null=True),
        ),
        migrations.AddField(
            model_name='atmosphereuser',
            name='uuid',
            field=models.UUIDField(null=True),
        ),
        migrations.AddField(
            model_name='applicationbookmark',
            name='uuid',
            field=models.UUIDField(null=True),
        ),
        migrations.AddField(
            model_name='bootscript',
            name='uuid',
            field=models.UUIDField(null=True),
        ),
        migrations.AddField(
            model_name='credential',
            name='uuid',
            field=models.UUIDField(null=True),
        ),
        migrations.AddField(
            model_name='group',
            name='uuid',
            field=models.UUIDField(null=True),
        ),
        migrations.AddField(
            model_name='identitymembership',
            name='uuid',
            field=models.UUIDField(null=True),
        ),
        migrations.AddField(
            model_name='instancemembership',
            name='uuid',
            field=models.UUIDField(null=True),
        ),
        migrations.AddField(
            model_name='instancesource',
            name='uuid',
            field=models.UUIDField(null=True),
        ),
        migrations.AddField(
            model_name='leadership',
            name='uuid',
            field=models.UUIDField(null=True),
        ),
        migrations.AddField(
            model_name='instancestatushistory',
            name='uuid',
            field=models.UUIDField(null=True),
        ),
        migrations.AddField(
            model_name='license',
            name='uuid',
            field=models.UUIDField(null=True),
        ),
        migrations.AddField(
            model_name='providercredential',
            name='uuid',
            field=models.UUIDField(null=True),
        ),
        migrations.AddField(
            model_name='quota',
            name='uuid',
            field=models.UUIDField(null=True),
        ),
        migrations.AddField(
            model_name='resourcerequest',
            name='uuid2',
            field=models.UUIDField(null=True),
        ),
        migrations.AddField(
            model_name='size',
            name='uuid',
            field=models.UUIDField(null=True),
        ),
        migrations.AddField(
            model_name='statustype',
            name='uuid',
            field=models.UUIDField(null=True),
        ),
        migrations.AddField(
            model_name='tag',
            name='uuid',
            field=models.UUIDField(null=True),
        ),
        migrations.AlterField(
            model_name='machinerequest',
            name='uuid',
            field=models.CharField(null=True, max_length=36),
        ),
        migrations.AlterField(
            model_name='resourcerequest',
            name='uuid',
            field=models.CharField(null=True, max_length=36),
        ),
    ]
