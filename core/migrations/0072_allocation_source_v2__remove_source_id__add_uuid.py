# -*- coding: utf-8 -*-
# Generated by Django 1.10.6 on 2017-03-09 19:23
from __future__ import unicode_literals

from django.db import migrations, models
import uuid


def gen_uuid(apps, schema_editor):
    AllocationSource = apps.get_model("core", "AllocationSource")
    for row in AllocationSource.objects.all():
        row.uuid = uuid.uuid4()
        row.save()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0071_allocation_source_v2__add_fields'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='allocationsource',
            name='source_id',
        ),
        # Data Migrations required,
        migrations.RunPython(
            gen_uuid, reverse_code=migrations.RunPython.noop),
        # Alterations
        migrations.AlterField(
            model_name='allocationsource',
            name='uuid',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
