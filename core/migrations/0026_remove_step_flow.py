# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0025_add_application_version_pt3'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='flow',
            name='created_by',
        ),
        migrations.RemoveField(
            model_name='flow',
            name='created_by_identity',
        ),
        migrations.RemoveField(
            model_name='flow',
            name='instance',
        ),
        migrations.RemoveField(
            model_name='flow',
            name='type',
        ),
        migrations.RemoveField(
            model_name='step',
            name='created_by',
        ),
        migrations.RemoveField(
            model_name='step',
            name='created_by_identity',
        ),
        migrations.RemoveField(
            model_name='step',
            name='flow',
        ),
        migrations.RemoveField(
            model_name='step',
            name='instance',
        ),
        migrations.DeleteModel(
            name='Flow',
        ),
        migrations.DeleteModel(
            name='FlowType',
        ),
        migrations.DeleteModel(
            name='Step',
        ),
    ]
