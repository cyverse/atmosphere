# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0032_auto_20150925_1239'),
    ]

    operations = [
        migrations.RenameField(
            model_name='applicationthreshold',
            old_name='storage_min',
            new_name='cpu_min',
        ),
    ]
