# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0009_add_quota_and_allocation_field_to_requests'),
    ]

    operations = [
        migrations.CreateModel(
            name='ApplicationTag', fields=[
                ('id', models.AutoField(
                    verbose_name='ID', serialize=False, auto_created=True, primary_key=True)), ], options={
                'db_table': 'application_tags', 'managed': False, }, bases=(
                        models.Model,), ), migrations.CreateModel(
                            name='InstanceTag', fields=[
                                ('id', models.AutoField(
                                    verbose_name='ID', serialize=False, auto_created=True, primary_key=True)), ], options={
                                        'db_table': 'instance_tags', 'managed': False, }, bases=(
                                            models.Model,), ), migrations.CreateModel(
                                                name='ProjectInstance', fields=[
                                                    ('id', models.AutoField(
                                                        verbose_name='ID', serialize=False, auto_created=True, primary_key=True)), ], options={
                                                            'db_table': 'project_instances', 'managed': False, }, bases=(
                                                                models.Model,), ), migrations.CreateModel(
                                                                    name='ProjectVolume', fields=[
                                                                        ('id', models.AutoField(
                                                                            verbose_name='ID', serialize=False, auto_created=True, primary_key=True)), ], options={
                                                                                'db_table': 'project_volumes', 'managed': False, }, bases=(
                                                                                    models.Model,), ), ]
