# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings
import core.models.status_type
import uuid

def create_status_types(apps, schema_editor):
    StatusType = apps.get_model("core", "StatusType")
    StatusType.objects.get_or_create(name="pending")
    StatusType.objects.get_or_create(name="closed")
    StatusType.objects.get_or_create(name="approved")
    StatusType.objects.get_or_create(name="rejected")
    StatusType.objects.get_or_create(name="started")

class Migration(migrations.Migration):
    dependencies = [
        ('core', '0039_threshold_rename_storagemin_to_cpumin')
    ]

    operations = [
        migrations.RunPython(create_status_types)
    ]
