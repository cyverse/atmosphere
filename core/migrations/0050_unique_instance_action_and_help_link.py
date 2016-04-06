# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


def update_instance_action_keys(apps, schema_editor):
    InstanceAction = apps.get_model("core", "InstanceAction")
    unique_keys = []
    for action in InstanceAction.objects.all():
        try:
            unique_key = action.name
            if unique_key in unique_keys:
                action.delete()
            else:
                action.key = unique_key
                action.save()
                unique_keys.append(unique_key)
        except Exception:
            raise


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0049_instancestatushistory_activity'),
    ]

    operations = [
        migrations.AddField(
            model_name='instanceaction',
            name='key',
            field=models.CharField(
                blank=True, null=True, unique=True, max_length=256),
        ),
        migrations.AlterField(
            model_name='helplink',
            name='link_key',
            field=models.CharField(unique=True, max_length=256, editable=False),
        ),
        migrations.AlterField(
            model_name='providerinstanceaction',
            name='instance_action',
            field=models.ForeignKey(related_name='provider_actions', to='core.InstanceAction'),
        ),
        migrations.AlterField(
            model_name='providerinstanceaction',
            name='provider',
            field=models.ForeignKey(related_name='provider_actions', to='core.Provider'),
        ),
        migrations.RunPython(update_instance_action_keys)
    ]
