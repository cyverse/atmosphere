# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0027_create_boot_scripts'),
    ]

    operations = [
        migrations.CreateModel(
            name='ApplicationVersionBootScript',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
            ],
            options={
                'db_table': 'application_version_boot_scripts',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='ApplicationVersionLicense',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
            ],
            options={
                'db_table': 'application_version_licenses',
                'managed': False,
            },
        ),
    ]
