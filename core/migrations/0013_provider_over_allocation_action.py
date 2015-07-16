# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


def add_default_action(apps, schema_editor):
    InstanceAction = apps.get_model("core", "InstanceAction")
    Provider = apps.get_model("core", "Provider")
    default_action = InstanceAction.objects.get(name="Suspend")
    for provider in Provider.objects.all():
        provider.over_allocation_action = default_action
        provider.save()


def do_nothing(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0012_remove_null_from_many_many'),
    ]

    operations = [
        migrations.AddField(
            model_name='provider',
            name='over_allocation_action',
            field=models.ForeignKey(
                blank=True,
                to='core.InstanceAction',
                null=True),
        ),
        migrations.RunPython(
            add_default_action,
            do_nothing),
    ]
