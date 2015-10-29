# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import uuid

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0034_uuid_data_for_all_the_things'),
    ]

    operations = [
        migrations.AlterField(
            model_name='application',
            name='uuid2',
            field=models.UUIDField(default=uuid.uuid4, unique=True, editable=False),
        ),
        migrations.AlterField(
            model_name='cloudadministrator',
            name='uuid2',
            field=models.UUIDField(default=uuid.uuid4, unique=True, editable=False),
        ),
        migrations.AlterField(
            model_name='identity',
            name='uuid2',
            field=models.UUIDField(default=uuid.uuid4, unique=True, editable=False),
        ),
        migrations.AlterField(
            model_name='machinerequest',
            name='uuid2',
            field=models.UUIDField(default=uuid.uuid4, unique=True, editable=False),
        ),
        migrations.AlterField(
            model_name='project',
            name='uuid2',
            field=models.UUIDField(default=uuid.uuid4, unique=True, editable=False),
        ),
        migrations.AlterField(
            model_name='provider',
            name='uuid2',
            field=models.UUIDField(default=uuid.uuid4, unique=True, editable=False),
        ),
        migrations.AlterField(
            model_name='allocation',
            name='uuid',
            field=models.UUIDField(default=uuid.uuid4, unique=True, editable=False),
        ),
        migrations.AlterField(
            model_name='applicationbookmark',
            name='uuid',
            field=models.UUIDField(default=uuid.uuid4, unique=True, editable=False),
        ),
        migrations.AlterField(
            model_name='atmosphereuser',
            name='uuid',
            field=models.UUIDField(default=uuid.uuid4, unique=True, editable=False),
        ),
        migrations.AlterField(
            model_name='bootscript',
            name='uuid',
            field=models.UUIDField(default=uuid.uuid4, unique=True, editable=False),
        ),
        migrations.AlterField(
            model_name='credential',
            name='uuid',
            field=models.UUIDField(default=uuid.uuid4, unique=True, editable=False),
        ),
        migrations.AlterField(
            model_name='group',
            name='uuid',
            field=models.UUIDField(default=uuid.uuid4, unique=True, editable=False),
        ),
        migrations.AlterField(
            model_name='identitymembership',
            name='uuid',
            field=models.UUIDField(default=uuid.uuid4, unique=True, editable=False),
        ),
        migrations.AlterField(
            model_name='instancemembership',
            name='uuid',
            field=models.UUIDField(default=uuid.uuid4, unique=True, editable=False),
        ),
        migrations.AlterField(
            model_name='instancesource',
            name='uuid',
            field=models.UUIDField(default=uuid.uuid4, unique=True, editable=False),
        ),
        migrations.AlterField(
            model_name='instancestatushistory',
            name='uuid',
            field=models.UUIDField(default=uuid.uuid4, unique=True, editable=False),
        ),
        migrations.AlterField(
            model_name='license',
            name='uuid',
            field=models.UUIDField(default=uuid.uuid4, unique=True, editable=False),
        ),
        migrations.AlterField(
            model_name='leadership',
            name='uuid',
            field=models.UUIDField(default=uuid.uuid4, unique=True, editable=False),
        ),
        migrations.AlterField(
            model_name='providercredential',
            name='uuid',
            field=models.UUIDField(default=uuid.uuid4, unique=True, editable=False),
        ),
        migrations.AlterField(
            model_name='quota',
            name='uuid',
            field=models.UUIDField(default=uuid.uuid4, unique=True, editable=False),
        ),
        migrations.AlterField(
            model_name='resourcerequest',
            name='uuid2',
            field=models.UUIDField(default=uuid.uuid4, unique=True, editable=False),
        ),
        migrations.AlterField(
            model_name='size',
            name='uuid',
            field=models.UUIDField(default=uuid.uuid4, unique=True, editable=False),
        ),
        migrations.AlterField(
            model_name='statustype',
            name='uuid',
            field=models.UUIDField(default=uuid.uuid4, unique=True, editable=False),
        ),
        migrations.AlterField(
            model_name='tag',
            name='uuid',
            field=models.UUIDField(default=uuid.uuid4, unique=True, editable=False),
        ),
    ]
