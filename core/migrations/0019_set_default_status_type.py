# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import core.models.status_type


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0018_add_allow_imaging_to_provider_machine'),
    ]

    operations = [
        migrations.AlterField(
            model_name='allocationrequest',
            name='status',
            field=models.ForeignKey(default=core.models.status_type.get_status_type_id, to='core.StatusType'),
        ),
        migrations.AlterField(
            model_name='quotarequest',
            name='status',
            field=models.ForeignKey(default=core.models.status_type.get_status_type_id, to='core.StatusType'),
        ),
    ]
