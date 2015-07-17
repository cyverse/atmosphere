# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import core.models.status_type


def copy_data_to_new_field(apps, schema_editor):
    MachineExport = apps.get_model("core", "MachineExport")
    for export in MachineExport.objects.all():
        export.source = export.instance.source
        export.save()


def do_nothing(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0014_drop_provider_membership_AND_make_forked_default_true'),
    ]

    operations = [
        migrations.AddField(
            model_name='machineexport', name='source', field=models.ForeignKey(
                blank=True, to='core.InstanceSource', null=True), ), migrations.RunPython(
            copy_data_to_new_field, do_nothing), migrations.RemoveField(
                    model_name='machineexport', name='instance', ), migrations.AlterField(
                        model_name='machineexport', name='source', field=models.ForeignKey(
                            to='core.InstanceSource'), ), ]
