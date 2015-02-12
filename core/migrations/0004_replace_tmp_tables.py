# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.utils.timezone
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_create_tmp_tables'),
    ]

    # switch to new tables
    operations = [
        migrations.RemoveField('Group', 'provider_machines'),
        migrations.RemoveField('ProviderMachineMembership', 'provider_machine'),
        migrations.RemoveField('Instance', 'source'),
        migrations.RemoveField('MachineRequest', 'new_machine'),
        migrations.RemoveField('MachineRequest', 'parent_machine'),
        migrations.RemoveField('Project', 'volumes'),
        migrations.RemoveField('VolumeStatusHistory', 'volume'),
        migrations.DeleteModel('ProviderMachine'),
        migrations.DeleteModel('Volume'),
        migrations.DeleteModel('InstanceSource'),
        migrations.RenameModel('InstanceSourceTmp', 'InstanceSource'),
        migrations.RenameModel('ProviderMachineTmp', 'ProviderMachine'),
        migrations.RenameModel('VolumeTmp', 'Volume'),
        migrations.RenameField('Group', 'provider_machines_tmp', 'provider_machines'),
        migrations.RenameField('ProviderMachineMembership', 'provider_machine_tmp', 'provider_machine'),
        migrations.RenameField('Instance', 'source_tmp', 'source'),
        migrations.RenameField('MachineRequest', 'new_machine_tmp', 'new_machine'),
        migrations.RenameField('MachineRequest', 'parent_machine_tmp', 'parent_machine'),
        migrations.RenameField('Project', 'volumes_tmp', 'volumes'),
        migrations.RenameField('VolumeStatusHistory', 'volume_tmp', 'volume'),
        migrations.AlterModelTable('InstanceSource', 'instance_source'),
        migrations.AlterModelTable('Volume', 'volume'),
        migrations.AlterModelTable('ProviderMachine', 'provider_machine'),
    ]
