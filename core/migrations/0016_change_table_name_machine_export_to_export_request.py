# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.utils.timezone
from django.conf import settings
import core.models.status_type


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0015_machine_export_instance_to_source'),
    ]

    operations = [
        migrations.CreateModel(
            name='ExportRequest', fields=[
                ('id', models.AutoField(
                    verbose_name='ID', serialize=False, auto_created=True, primary_key=True)), ('status', models.CharField(
                        max_length=256)), ('export_name', models.CharField(
                            max_length=256)), ('export_format', models.CharField(
                                max_length=256)), ('export_file', models.CharField(
                                    max_length=256, null=True, blank=True)), ('start_date', models.DateTimeField(
                                        default=django.utils.timezone.now)), ('end_date', models.DateTimeField(
                                            null=True, blank=True)), ('export_owner', models.ForeignKey(
                                                to=settings.AUTH_USER_MODEL)), ('source', models.ForeignKey(
                                                    to='core.InstanceSource')), ], options={
                'db_table': 'export_request', }, ), migrations.RemoveField(
            model_name='machineexport', name='export_owner', ), migrations.RemoveField(
            model_name='machineexport', name='source', ), migrations.DeleteModel(
            name='MachineExport', ), ]
