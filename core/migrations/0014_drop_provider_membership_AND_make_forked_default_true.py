# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import core.models.status_type


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0013_provider_over_allocation_action'),
    ]

    operations = [
        migrations.AlterField(
            model_name='machinerequest',
            name='new_machine_forked',
            field=models.BooleanField(default=True),
        ),
        migrations.AlterUniqueTogether(
            name='providermembership',
            unique_together=set([]),
        ),
        migrations.RemoveField(
            model_name='providermembership',
            name='member',
        ),
        migrations.RemoveField(
            model_name='providermembership',
            name='provider',
        ),
        migrations.RemoveField(
            model_name='group',
            name='providers',
        ),
        migrations.DeleteModel(
            name='ProviderMembership',
        ),
    ]
