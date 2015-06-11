# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0023_application_version_add_and_fill_and_delete'),
    ]

    operations = [
        migrations.AddField(
            model_name='applicationthreshold',
            name='application_version',
            field=models.OneToOneField(related_name='threshold', null=True, blank=True, to='core.ApplicationVersion'),
        ),
        migrations.AddField(
            model_name='applicationversion',
            name='excluded_files',
            field=models.TextField(default=b'', null=True, blank=True),
        ),
        migrations.AddField(
            model_name='applicationversion',
            name='installed_software',
            field=models.TextField(default=b'', null=True, blank=True),
        ),
        migrations.AddField(
            model_name='applicationversion',
            name='iplant_system_files',
            field=models.TextField(default=b'', null=True, blank=True),
        ),
        migrations.AddField(
            model_name='machinerequest',
            name='new_application_name',
            field=models.CharField(max_length=256, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='machinerequest',
            name='new_application_version',
            field=models.ForeignKey(blank=True, to='core.ApplicationVersion', null=True),
        ),
        migrations.AddField(
            model_name='machinerequest',
            name='new_version_allow_imaging',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='machinerequest',
            name='new_version_description',
            field=models.TextField(default=b'', null=True, blank=True),
        ),
        migrations.AddField(
            model_name='machinerequest',
            name='new_version_forked',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='machinerequest',
            name='new_version_licenses',
            field=models.ManyToManyField(to='core.License', blank=True),
        ),
        migrations.AddField(
            model_name='machinerequest',
            name='new_version_membership',
            field=models.ManyToManyField(to='core.Group', blank=True),
        ),
        migrations.AddField(
            model_name='machinerequest',
            name='new_version_memory_min',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='machinerequest',
            name='new_version_storage_min',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='machinerequest',
            name='new_version_tags',
            field=models.TextField(default=b'', null=True, blank=True),
        ),
        migrations.AddField(
            model_name='machinerequest',
            name='new_version_visibility',
            field=models.CharField(max_length=256, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='applicationversion',
            name='name',
            field=models.CharField(max_length=32, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='machinerequest',
            name='access_list',
            field=models.TextField(default=b'', null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='machinerequest',
            name='exclude_files',
            field=models.TextField(default=b'', null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='machinerequest',
            name='installed_software',
            field=models.TextField(default=b'', null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='machinerequest',
            name='iplant_sys_files',
            field=models.TextField(default=b'', null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='machinerequest',
            name='new_machine',
            field=models.ForeignKey(blank=True, to='core.ProviderMachine', null=True),
        ),
        migrations.AlterField(
            model_name='machinerequest',
            name='new_machine_licenses',
            field=models.ManyToManyField(related_name='_machine_request', to='core.License', blank=True),
        ),
        migrations.AlterField(
            model_name='machinerequest',
            name='status',
            field=models.TextField(default=b'', null=True, blank=True),
        ),
    ]
