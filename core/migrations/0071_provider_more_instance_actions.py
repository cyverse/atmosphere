# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


def copy_data_to_new_models(apps, schema_editor):
    Provider = apps.get_model("core", "Provider")
    InstanceAction = apps.get_model("core", "InstanceAction")
    ProviderInstanceAction = apps.get_model("core", "ProviderInstanceAction")
    add_instance_actions(Provider, InstanceAction, ProviderInstanceAction)
    return


def add_instance_actions(Provider, InstanceAction, ProviderInstanceAction):
    InstanceAction.objects.get_or_create(
        name="Redeploy",
        key="Redeploy",
        description="""Redeploy to an instance when it is in ANY active state""")

    instance_actions = InstanceAction.objects.all()
    for provider in Provider.objects.all():
        for action in instance_actions:
            ProviderInstanceAction.objects.get_or_create(
                provider_id=provider.id,
                instance_action_id=action.id)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0070_provider_created_by'),
    ]

    operations = [
        migrations.RunPython(
            copy_data_to_new_models, migrations.RunPython.noop),
    ]
