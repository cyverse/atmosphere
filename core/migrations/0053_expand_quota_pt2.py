# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0052_expand_quota'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='quota',
            name='suspended_count',
        ),
    ]
