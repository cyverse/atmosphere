from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings
import core.models.status_type
import uuid

def update_status_types(apps, schema_editor):
    StatusType = apps.get_model("core", "StatusType")
    StatusType.objects.get_or_create(name="denied")
    StatusType.delete(StatusType.objects.get(name="rejected"))

class Migration(migrations.Migration):
    dependencies = [
        ('core', '0053_expand_quota_pt2')
    ]

    operations = [
        migrations.RunPython(update_status_types)
    ]
