# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.utils.timezone
from django.conf import settings


def create_machine(apps, old_machine):
    InstanceSourceTmp = apps.get_model("core", "InstanceSourceTmp")
    Instance = apps.get_model("core", "Instance")
    ProviderMachineTmp = apps.get_model("core", "ProviderMachineTmp")

    old_source = old_machine.instancesource_ptr
    source = InstanceSourceTmp.objects.create(
        provider=old_source.provider,
        identifier=old_source.identifier,
        created_by=old_source.created_by,
        created_by_identity=old_source.created_by_identity,
        start_date=old_source.start_date,
        end_date=old_source.end_date
    )

    # Update instance pointers
    instances = Instance.objects.filter(
        source_id=old_machine.instancesource_ptr_id)

    for instance in instances:
        instance.source_tmp = source
        instance.save()

    return ProviderMachineTmp.objects.create(
        application_id=old_machine.application.id,
        version=old_machine.version,
        instance_source=source
    )


def copy_data_to_new_models(apps, schema_editor):
    Instance = apps.get_model("core", "Instance")
    InstanceSourceTmp = apps.get_model("core", "InstanceSourceTmp")
    ProviderMachine = apps.get_model("core", "ProviderMachine")
    VolumeTmp = apps.get_model("core", "VolumeTmp")
    Volume = apps.get_model("core", "Volume")

    volumes = Volume.objects.all()
    machines = ProviderMachine.objects.all()

    machine_cache = {}

    for machine in machines:
        if machine.id not in machine_cache:
            new_machine = create_machine(apps, machine)
            machine_cache[machine.id] = new_machine
        else:
            new_machine = machine_cache[machine.id]

        new_machine.licenses = machine.licenses.all()
        new_machine.save()

        # Update membership
        members = machine.providermachinemembership_set.all()

        for member in members:
            member.provider_machine_tmp = new_machine
            member.save()

        # Update machine requests
        MachineRequest = apps.get_model("core", "MachineRequest")
        machine_requests = MachineRequest.objects.filter(new_machine_id=machine.id)

        for machine_request in machine_requests:
            machine_request.new_machine_tmp_id = new_machine.id
            try:
                parent = machine_request.parent_machine
            except:
                parent = None

            if parent:
                if parent.id not in machine_cache:
                    new_parent = create_machine(apps, parent)
                    machine_cache[parent.id] = new_parent
                else:
                    new_parent = machine_cache[parent.id]

                machine_request.parent_machine_tmp_id = new_parent.id

            machine_request.save()

    for volume in volumes:
        old_source = volume.instancesource_ptr
        source = InstanceSourceTmp.objects.create(
            provider=old_source.provider,
            identifier=old_source.identifier,
            created_by=old_source.created_by,
            created_by_identity=old_source.created_by_identity,
            start_date=old_source.start_date,
            end_date=old_source.end_date
        )

        # Update instance pointers
        instances = Instance.objects.filter(source_id=volume.instancesource_ptr_id)

        for instance in instances:
            instance.source_tmp = source
            instance.save()

        new_volume = VolumeTmp.objects.create(
            size=volume.size,
            name=volume.name,
            description=volume.description,
            instance_source=source
        )

        # Update volume status history
        history = volume.volumestatushistory_set.all()

        for entry in history:
            entry.volume_tmp = new_volume
            entry.save()


def copy_data_to_old_model(apps, schema_editor):
    ProviderMachineTmp = apps.get_model("core", "ProviderMachineTmp")
    ProviderMachine = apps.get_model("core", "ProviderMachine")
    VolumeTmp = apps.get_model("core", "VolumeTmp")
    Volume = apps.get_model("core", "Volume")

    volumes = VolumeTmp.objects.all()
    machines = ProviderMachineTmp.objects.all()

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_auto_20150205_1056'),
    ]

    operations = [
        migrations.CreateModel(
            name='InstanceSourceTmp',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('identifier', models.CharField(max_length=256)),
                ('start_date', models.DateTimeField(default=django.utils.timezone.now)),
                ('end_date', models.DateTimeField(null=True, blank=True)),
                ('created_by', models.ForeignKey(related_name='source_set', blank=True, to=settings.AUTH_USER_MODEL, null=True)),
                ('created_by_identity', models.ForeignKey(blank=True, to='core.Identity', null=True)),
                ('provider', models.ForeignKey(to='core.Provider')),
            ],
            options={
                'db_table': 'instance_source_tmp',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ProviderMachineTmp',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('version', models.CharField(default=b'1.0.0', max_length=128)),
                ('application', models.ForeignKey(to='core.Application')),
                ('instance_source', models.OneToOneField(to='core.InstanceSourceTmp')),
                ('licenses', models.ManyToManyField(to='core.License', null=True, blank=True)),
            ],
            options={
                'db_table': 'provider_machine_tmp',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='VolumeTmp',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('size', models.IntegerField()),
                ('name', models.CharField(max_length=256)),
                ('description', models.TextField(null=True, blank=True)),
                ('instance_source', models.OneToOneField(to='core.InstanceSourceTmp')),
            ],
            options={
                'db_table': 'volume_tmp',
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='instance',
            name='source_tmp',
            field=models.ForeignKey(related_name='instances', to='core.InstanceSourceTmp', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='machinerequest',
            name='new_machine_tmp',
            field=models.ForeignKey(related_name='created_machine', blank=True, to='core.ProviderMachineTmp', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='machinerequest',
            name='parent_machine_tmp',
            field=models.ForeignKey(related_name='ancestor_machine', to='core.ProviderMachineTmp', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='providermachinemembership',
            name='provider_machine_tmp',
            field=models.ForeignKey(to='core.ProviderMachineTmp', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='volumestatushistory',
            name='volume_tmp',
            field=models.ForeignKey(to='core.VolumeTmp', null=True),
            preserve_default=True,
        ),
        migrations.RunPython(copy_data_to_new_models)
    ]
