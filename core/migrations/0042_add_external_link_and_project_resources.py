# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0041_user_ssh_keys'),
    ]

    operations = [
        migrations.CreateModel(
            name='ExternalLink',
            fields=[
                ('id', models.UUIDField(primary_key=True, default=uuid.uuid4, serialize=False, editable=False, unique=True)),
                ('title', models.CharField(max_length=256)),
                ('link', models.URLField(max_length=256)),
                ('description', models.TextField(null=True, blank=True)),
                ('created_by', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'external_link',
            },
        ),
        migrations.AddField(
            model_name='project',
            name='links',
            field=models.ManyToManyField(related_name='projects', to='core.ExternalLink', blank=True),
        ),
        migrations.CreateModel(
            name='ProjectApplication',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
            ],
            options={
                'db_table': 'project_applications',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='ProjectExternalLink',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
            ],
            options={
                'db_table': 'project_externallinks',
                'managed': False,
            },
        ),
    ]
