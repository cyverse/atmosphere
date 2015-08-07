# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.utils.timezone
from django.conf import settings
import uuid
import json


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0022_remove_quota_and_allocation_request'),
    ]

    operations = [
        migrations.CreateModel(
            name='ApplicationVersion', fields=[
                ('id', models.UUIDField(
                    default=uuid.uuid4, serialize=False, editable=False, primary_key=True)), ('name', models.CharField(
                        max_length=256)), ('change_log', models.TextField(
                            null=True, blank=True)), ('allow_imaging', models.BooleanField(
                                default=True)), ('start_date', models.DateTimeField(
                                    default=django.utils.timezone.now)), ('end_date', models.DateTimeField(
                                        null=True, blank=True)), ('iplant_system_files', models.TextField(
                                            default=b'', null=True, blank=True)), ('installed_software', models.TextField(
                                                default=b'', null=True, blank=True)), ('excluded_files', models.TextField(
                                                    default=b'', null=True, blank=True)), ], options={
                'db_table': 'application_version', }, ), migrations.CreateModel(
            name='ApplicationVersionMembership', fields=[
                ('id', models.AutoField(
                    verbose_name='ID', serialize=False, auto_created=True, primary_key=True)), ('can_share', models.BooleanField(
                        default=False)), ('application_version', models.ForeignKey(
                            to='core.ApplicationVersion')), ('group', models.ForeignKey(
                                to='core.Group')), ], options={
                'db_table': 'application_version_membership', }, ), migrations.RenameField(
            model_name='machinerequest', old_name='new_machine_allow_imaging', new_name='new_version_allow_imaging', ), migrations.RenameField(
            model_name='machinerequest', old_name='new_machine_forked', new_name='new_version_forked', ), migrations.RenameField(
            model_name='machinerequest', old_name='new_machine_licenses', new_name='new_version_licenses', ), migrations.RenameField(
            model_name='machinerequest', old_name='new_machine_memory_min', new_name='new_version_memory_min', ), migrations.RenameField(
            model_name='machinerequest', old_name='new_machine_storage_min', new_name='new_version_storage_min', ), migrations.AddField(
            model_name='machinerequest', name='new_application_description', field=models.TextField(
                default=b'', null=True, blank=True), ), migrations.AddField(
            model_name='machinerequest', name='new_application_name', field=models.CharField(
                max_length=256, null=True, blank=True), ), migrations.AddField(
            model_name='machinerequest', name='new_application_visibility', field=models.CharField(
                max_length=256, null=True, blank=True), ), migrations.AddField(
            model_name='machinerequest', name='new_version_change_log', field=models.TextField(
                default=b'', null=True, blank=True), ), migrations.AddField(
            model_name='machinerequest', name='new_version_membership', field=models.ManyToManyField(
                to='core.Group', blank=True), ), migrations.AddField(
            model_name='machinerequest', name='new_version_name', field=models.CharField(
                max_length=256, null=True, blank=True), ), migrations.AddField(
            model_name='machinerequest', name='new_version_tags', field=models.TextField(
                default=b'', null=True, blank=True), ), migrations.AlterField(
            model_name='machinerequest', name='access_list', field=models.TextField(
                default=b'', null=True, blank=True), ), migrations.AlterField(
            model_name='machinerequest', name='exclude_files', field=models.TextField(
                default=b'', null=True, blank=True), ), migrations.AlterField(
            model_name='machinerequest', name='installed_software', field=models.TextField(
                default=b'', null=True, blank=True), ), migrations.AlterField(
            model_name='machinerequest', name='iplant_sys_files', field=models.TextField(
                default=b'', null=True, blank=True), ), migrations.AlterField(
            model_name='machinerequest', name='new_machine', field=models.ForeignKey(
                blank=True, to='core.ProviderMachine', null=True), ), migrations.AlterField(
            model_name='machinerequest', name='status', field=models.TextField(
                default=b'', null=True, blank=True), ), migrations.AddField(
            model_name='applicationversion', name='application', field=models.ForeignKey(
                related_name='versions', to='core.Application'), ), migrations.AddField(
            model_name='applicationversion', name='created_by', field=models.ForeignKey(
                to=settings.AUTH_USER_MODEL), ), migrations.AddField(
            model_name='applicationversion', name='created_by_identity', field=models.ForeignKey(
                to='core.Identity', null=True), ), migrations.AddField(
            model_name='applicationversion', name='parent', field=models.ForeignKey(
                to='core.ApplicationVersion', null=True, blank=True), ), migrations.AddField(
            model_name='applicationversion', name='licenses', field=models.ManyToManyField(
                related_name='application_versions', to='core.License', blank=True), ), migrations.AddField(
            model_name='applicationversion', name='membership', field=models.ManyToManyField(
                related_name='application_versions', through='core.ApplicationVersionMembership', to='core.Group', blank=True), ), migrations.AddField(
            model_name='applicationthreshold', name='application_version', field=models.OneToOneField(
                related_name='threshold', null=True, blank=True, to='core.ApplicationVersion'), ), migrations.AddField(
            model_name='machinerequest', name='new_application_version', field=models.ForeignKey(
                blank=True, to='core.ApplicationVersion', null=True), ), migrations.AddField(
            model_name='providermachine', name='application_version', field=models.ForeignKey(
                related_name='machines', to='core.ApplicationVersion', null=True), ), migrations.AlterUniqueTogether(
            name='applicationversionmembership', unique_together=set(
                [
                    ('application_version', 'group')]), ), migrations.AlterUniqueTogether(
            name='applicationversion', unique_together=set(
                [
                    ('application', 'name')]), ), ]
