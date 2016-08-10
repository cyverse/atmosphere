# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='TASAllocationReport',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('username', models.CharField(max_length=128)),
                ('project_name', models.CharField(max_length=128)),
                ('queue_name', models.CharField(max_length=128, default="Atmosphere")),
                ('resource_name', models.CharField(max_length=128, default="Jetstream")),
                ('tacc_api', models.CharField(max_length=512)),
                ('scheduler_id', models.CharField(max_length=128, default="use.jetstream-cloud.org")),
                ('compute_used', models.DecimalField(max_digits=19, decimal_places=3)),
                ('start_date', models.DateTimeField()),
                ('end_date', models.DateTimeField()),
                ('report_date', models.DateTimeField(blank=True, null=True)),
                ('success', models.BooleanField(default=False)),
                ('user', models.ForeignKey(related_name='tas_reports', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
