# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0063_update_atmosphere_user_field_length'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='userprofile',
            name='use_ssh_keys',
        ),
    ]
