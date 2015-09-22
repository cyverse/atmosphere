# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='token',
            old_name='user_agent',
            new_name='issuer',
        ),
        migrations.AlterField(
            model_name='token',
            name='key',
            field=models.CharField(max_length=1024, serialize=False, primary_key=True),
        ),
    ]
