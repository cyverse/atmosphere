# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0044_cm_defaults_for_allocation_and_quota'),
    ]

    operations = [
        migrations.AlterField(
            model_name='machinerequest',
            name='new_version_membership',
            field=models.ManyToManyField(to='core.Group', blank=True),
        ),
        migrations.AlterModelTable(
            name='projectexternallink',
            table='project_links',
        ),
    ]
