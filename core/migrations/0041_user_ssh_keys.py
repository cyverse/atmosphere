# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0040_auto_add_status_types'),
    ]

    operations = [
        migrations.CreateModel(
            name='SSHKey',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=256)),
                ('uuid', models.CharField(default=uuid.uuid4, unique=True, max_length=36)),
                ('pub_key', models.TextField()),
                ('atmo_user', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'ssh_key',
            },
        ),
        migrations.AddField(
            model_name='userprofile',
            name='use_ssh_keys',
            field=models.BooleanField(default=False),
        ),
    ]
