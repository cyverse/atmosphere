from __future__ import unicode_literals

from django.db import migrations


def update_status_types(apps, schema_editor):
    StatusType = apps.get_model("core", "StatusType")
    StatusType.objects.get_or_create(name="denied")
    StatusType.delete(StatusType.objects.get(name="rejected"))


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0059_instance__web_desktop')
    ]

    operations = [
        migrations.RunPython(update_status_types)
    ]
