# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import core.models.status_type


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0017_add_pattern_match_to_license'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='license',
            name='allow_imaging',
        ),
        migrations.AddField(
            model_name='machinerequest',
            name='new_machine_allow_imaging',
            field=models.BooleanField(
                default=True),
        ),
        migrations.AddField(
            model_name='providermachine',
            name='allow_imaging',
            field=models.BooleanField(
                default=True),
        ),
        migrations.AlterField(
            model_name='providermachine',
            name='licenses',
            field=models.ManyToManyField(
                related_name='machines',
                to='core.License',
                blank=True),
        ),
    ]
