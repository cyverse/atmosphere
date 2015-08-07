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
        # Point many-to-many fields to tmp models
        migrations.AlterField(
            model_name='group',
            name='provider_machines',
            field=models.ManyToManyField(
                related_name='members',
                through='core.ProviderMachineMembership',
                to='core.ProviderMachineTmp',
                blank=True),
        ),
        migrations.AlterField(
            model_name='project',
            name='volumes',
            field=models.ManyToManyField(
                related_name='projects',
                to='core.VolumeTmp',
                blank=True,
                null=True),
            preserve_default=True,
        ),

        # Remove old references
        migrations.RemoveField('Instance', 'source'),
        migrations.RemoveField('MachineRequest', 'new_machine'),
        migrations.RemoveField('MachineRequest', 'parent_machine'),
        migrations.RemoveField('VolumeStatusHistory', 'volume'),
        migrations.RemoveField(
            'ProviderMachineMembership',
            'provider_machine'),

        # Rename fields
        migrations.RenameField(
            'ProviderMachineMembership',
            'provider_machine_tmp',
            'provider_machine'),
        migrations.RenameField('Instance', 'source_tmp', 'source'),
        migrations.RenameField(
            'MachineRequest',
            'new_machine_tmp',
            'new_machine'),
        migrations.RenameField(
            'MachineRequest',
            'parent_machine_tmp',
            'parent_machine'),
        migrations.RenameField('VolumeStatusHistory', 'volume_tmp', 'volume'),

        # Delete old models
        migrations.DeleteModel('ProviderMachine'),
        migrations.DeleteModel('Volume'),
        migrations.DeleteModel('InstanceSource'),

        # Update database model names
        migrations.AlterModelTable('InstanceSourceTmp', 'instance_source'),
        migrations.AlterModelTable('VolumeTmp', 'volume'),
        migrations.AlterModelTable('ProviderMachineTmp', 'provider_machine'),

        # Rename new models
        migrations.RenameModel('InstanceSourceTmp', 'InstanceSource'),
        migrations.RenameModel('ProviderMachineTmp', 'ProviderMachine'),
        migrations.RenameModel('VolumeTmp', 'Volume'),

        # Alter Fields to point to new models
        migrations.AlterField(
            model_name='providermachine',
            name='instance_source',
            field=models.OneToOneField(to='core.InstanceSource'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='volume',
            name='instance_source',
            field=models.OneToOneField(to='core.InstanceSource'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='group',
            name='provider_machines',
            field=models.ManyToManyField(
                related_name='members',
                through='core.ProviderMachineMembership',
                to='core.ProviderMachine',
                blank=True),
        ),
        migrations.AlterField(
            model_name='project',
            name='volumes',
            field=models.ManyToManyField(
                related_name='projects',
                to='core.Volume',
                blank=True,
                null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='instance',
            name='source',
            field=models.ForeignKey(
                related_name='instances',
                to='core.InstanceSource',
                null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='machinerequest',
            name='new_machine',
            field=models.ForeignKey(
                related_name='created_machine',
                blank=True,
                to='core.ProviderMachine',
                null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='machinerequest',
            name='parent_machine',
            field=models.ForeignKey(
                related_name='ancestor_machine',
                to='core.ProviderMachine',
                null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='providermachinemembership',
            name='provider_machine',
            field=models.ForeignKey(to='core.ProviderMachine', null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='volumestatushistory',
            name='volume',
            field=models.ForeignKey(to='core.Volume', null=True),
            preserve_default=True,
        ),

        # Add constrants
        migrations.AlterUniqueTogether(
            name='instancesource',
            unique_together=set([('provider', 'identifier')]),
        ),
    ]
