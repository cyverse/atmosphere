from __future__ import unicode_literals

from django.db import models, migrations


def remove_null_entries(apps, schema_editor):
    ProviderMachineMembership = apps.get_model(
        "core", "ProviderMachineMembership")
    MachineRequest = apps.get_model("core", "MachineRequest")

    memberships = ProviderMachineMembership.objects.filter(
        provider_machine=None)
    requests = MachineRequest.objects.filter(parent_machine=None)

    memberships.delete()
    requests.delete()


def do_nothing(apps, schema_editor):
    """
    Do nothing since this is removing bad data
    """


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_replace_tmp_tables'),
    ]

    operations = [
        migrations.RunPython(remove_null_entries, do_nothing),
    ]
