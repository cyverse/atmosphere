# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0026_remove_step_flow'),
    ]

    operations = [
        migrations.AddField(
            model_name='applicationversion',
            name='boot_scripts',
            field=models.ManyToManyField(related_name='application_versions', to='core.BootScript', blank=True),
        ),
        migrations.AlterField(
            model_name='application',
            name='icon',
            field=models.ImageField(null=True, upload_to=b'applications', blank=True),
        ),
    ]
