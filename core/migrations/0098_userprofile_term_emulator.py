# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0097_userprofile_guacamole_color'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='term_emulator',
            field=models.CharField(default=b'default', max_length=255),
        ),
    ]
