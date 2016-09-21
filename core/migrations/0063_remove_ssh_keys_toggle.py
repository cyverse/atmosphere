# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0062_update_templates_with_cyverse'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='userprofile',
            name='use_ssh_keys',
        ),
    ]
