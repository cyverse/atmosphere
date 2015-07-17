# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


def remove_null_entries(apps, schema_editor):
    ProviderMachineMembership = apps.get_model(
        "core",
        "ProviderMachineMembership")
    MachineRequest = apps.get_model("core", "MachineRequest")

    memberships = ProviderMachineMembership.objects.filter(
        provider_machine=None)
    requests = MachineRequest.objects.filter(parent_machine=None)

    memberships.delete()
    requests.delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_delete_null_fields'),
    ]

    operations = [
        migrations.RunPython(remove_null_entries),
        migrations.AlterField(
            model_name='instance', name='source', field=models.ForeignKey(
                related_name='instances', to='core.InstanceSource'),
            preserve_default=True,),
        migrations.AlterField(
            model_name='providermachinemembership', name='provider_machine',
            field=models.ForeignKey(to='core.ProviderMachine'),
            preserve_default=True,),
        migrations.AlterField(
            model_name='machinerequest', name='parent_machine',
            field=models.ForeignKey(
                related_name='ancestor_machine', to='core.ProviderMachine'),
            preserve_default=True,),
        migrations.AlterField(
            model_name='volumestatushistory', name='volume',
            field=models.ForeignKey(to='core.Volume'),
            preserve_default=True,), ]
