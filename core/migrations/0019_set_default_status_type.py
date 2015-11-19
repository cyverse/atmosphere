# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


def apply_data_migration(apps, schema_editor):
    StatusType = apps.get_model("core", "StatusType")
    add_status_types(StatusType)


def add_status_types(StatusType):
    StatusType.objects.get_or_create(name="pending")
    return


def go_back(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0018_add_allow_imaging_to_provider_machine'),
    ]

    operations = [
        migrations.RunPython(
            apply_data_migration, go_back),
        migrations.AlterField(
            model_name='allocationrequest',
            name='status',
            field=models.ForeignKey(
                default=1,
                to='core.StatusType'),
        ),
        migrations.AlterField(
            model_name='quotarequest',
            name='status',
            field=models.ForeignKey(
                default=1,
                to='core.StatusType'),
        ),
    ]
