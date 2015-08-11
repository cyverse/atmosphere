# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0028_add_version_license_and_scripts'),
    ]

    operations = [
        migrations.AddField(
            model_name='machinerequest',
            name='new_version_scripts',
            field=models.ManyToManyField(to='core.BootScript', blank=True),
        ),
    ]
