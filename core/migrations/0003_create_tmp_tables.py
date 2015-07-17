# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.utils.timezone
from django.conf import settings


def create_volume(old_volume, Instance, InstanceSourceTmp, VolumeTmp):

    old_source = old_volume.instancesource_ptr
    source = InstanceSourceTmp.objects.create(
        provider=old_source.provider,
        identifier=old_source.identifier,
        created_by=old_source.created_by,
        created_by_identity=old_source.created_by_identity,
        start_date=old_source.start_date,
        end_date=old_source.end_date
    )

    new_volume = VolumeTmp.objects.create(
        size=old_volume.size,
        name=old_volume.name,
        description=old_volume.description,
        instance_source=source
    )

    # Update old_volume status projects

    #    for entry in projects:

    # Update old_volume status history
    history = old_volume.volumestatushistory_set.all()

    for entry in history:
        entry.volume_tmp = new_volume
        entry.save()


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

    return ProviderMachineTmp.objects.create(
        application_id=old_machine.application.id,
        version=old_machine.version,
        instance_source=source
    )


def restore_machine_request(machine_request, ProviderMachine, machine_cache):
    try:
        parent = ProviderMachine.objects.get(
            id=machine_request.parent_machine_id)
    except ProviderMachine.DoesNotExist:
        machine_request.parent_machine = machine_request.instance.source.providermachine
        machine_request.save()
        parent = ProviderMachine.objects.get(
            id=machine_request.parent_machine.id)

    new_parent_machine = machine_cache[parent.id]
    machine_request.parent_machine_tmp_id = new_parent_machine.id

    if machine_request.new_machine_id:
        try:
            new_machine = machine_request.new_machine
            new_new_machine = machine_cache[new_machine.id]
            machine_request.new_machine_tmp_id = new_new_machine.id
        except Exception as dne:
            print 'Warn: The new machine created from Instance %s (Named %s) has been lost (Provider %s)'\
                % (machine_request.instance.provider_alias,
                   machine_request.new_machine_name,
                   machine_request.new_machine_provider.location)
            machine_request.new_machine_id = None

    machine_request.save()


def associate_instance(instance, InstanceSourceTmp):
    new_source = InstanceSourceTmp.objects.get(
        identifier=instance.source.identifier,
        provider=instance.source.provider)
    instance.source_tmp = new_source
    instance.save()


def associate_machine(machine, new_machine):

    new_machine.licenses = machine.licenses.all()
    new_machine.save()

    # Update membership
    members = machine.providermachinemembership_set.all()

    for member in members:
        member.provider_machine_tmp = new_machine
        member.save()


def copy_data_to_new_models(apps, schema_editor):
    Instance = apps.get_model("core", "Instance")
    InstanceSourceTmp = apps.get_model("core", "InstanceSourceTmp")
    VolumeTmp = apps.get_model("core", "VolumeTmp")
    ProviderMachine = apps.get_model("core", "ProviderMachine")
    Volume = apps.get_model("core", "Volume")
    MachineRequest = apps.get_model("core", "MachineRequest")
    Instance = apps.get_model("core", "Instance")
    InstanceSourceTmp = apps.get_model("core", "InstanceSourceTmp")

    volumes = Volume.objects.order_by('id')
    machines = ProviderMachine.objects.order_by('id')
    machine_requests = MachineRequest.objects.order_by('id')
    instances = Instance.objects.order_by('id')
    print " ...\nThis can take a while..."
    machine_cache = {}
    started_at = django.utils.timezone.now()
    for machine in machines:
        new_machine = create_machine(apps, machine)
        machine_cache[machine.id] = new_machine
    for machine in machines:
        new_machine = machine_cache[machine.id]
        associate_machine(machine, new_machine)
    print "Created %s machines - %s" % (machines.count(), django.utils.timezone.now() - started_at)

    started_at = django.utils.timezone.now()
    for machine_request in machine_requests:
        restore_machine_request(
            machine_request,
            ProviderMachine,
            machine_cache)
    print "Updated %s machine_requests - %s" % (machine_requests.count(), django.utils.timezone.now() - started_at)

    started_at = django.utils.timezone.now()
    for volume in volumes:
        create_volume(volume, Instance, InstanceSourceTmp, VolumeTmp)
    print "Created %s Volumes %s" % (volumes.count(), django.utils.timezone.now() - started_at)

    started_at = django.utils.timezone.now()
    for instance in instances:
        associate_instance(instance, InstanceSourceTmp)
    print "Updated %s Instances %s" % (instances.count(), django.utils.timezone.now() - started_at)
    print "Completed!"


def do_nothing(apps, schema_editor):
    return


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_add_cloud_administrator'),
    ]

    operations = [
        migrations.CreateModel(
            name='InstanceSourceTmp', fields=[
                ('id', models.AutoField(
                    verbose_name='ID', serialize=False, auto_created=True, primary_key=True)), ('identifier', models.CharField(
                        max_length=256)), ('start_date', models.DateTimeField(
                            default=django.utils.timezone.now)), ('end_date', models.DateTimeField(
                                null=True, blank=True)), ('created_by', models.ForeignKey(
                                    related_name='source_set', blank=True, to=settings.AUTH_USER_MODEL, null=True)), ('created_by_identity', models.ForeignKey(
                                        blank=True, to='core.Identity', null=True)), ('provider', models.ForeignKey(
                                            to='core.Provider')), ], options={
                'db_table': 'instance_source_tmp', }, bases=(
                                                models.Model,), ), migrations.CreateModel(
                                                    name='ProviderMachineTmp', fields=[
                                                        ('id', models.AutoField(
                                                            verbose_name='ID', serialize=False, auto_created=True, primary_key=True)), ('version', models.CharField(
                                                                default=b'1.0.0', max_length=128)), ('application', models.ForeignKey(
                                                                    to='core.Application')), ('instance_source', models.OneToOneField(
                                                                        to='core.InstanceSourceTmp')), ('licenses', models.ManyToManyField(
                                                                            to='core.License', null=True, blank=True)), ], options={
                                                                                'db_table': 'provider_machine_tmp', }, bases=(
                                                                                    models.Model,), ), migrations.CreateModel(
                                                                                        name='VolumeTmp', fields=[
                                                                                            ('id', models.AutoField(
                                                                                                verbose_name='ID', serialize=False, auto_created=True, primary_key=True)), ('size', models.IntegerField()), ('name', models.CharField(
                                                                                                    max_length=256)), ('description', models.TextField(
                                                                                                        null=True, blank=True)), ('instance_source', models.OneToOneField(
                                                                                                            to='core.InstanceSourceTmp')), ], options={
                                                                                                                'db_table': 'volume_tmp', }, bases=(
                                                                                                                    models.Model,), ), migrations.AddField(
                                                                                                                        model_name='instance', name='source_tmp', field=models.ForeignKey(
                                                                                                                            related_name='instances', to='core.InstanceSourceTmp', null=True), preserve_default=True, ), migrations.AddField(
                                                                                                                                model_name='machinerequest', name='new_machine_tmp', field=models.ForeignKey(
                                                                                                                                    related_name='created_machine', blank=True, to='core.ProviderMachineTmp', null=True), preserve_default=True, ), migrations.AddField(
                                                                                                                                        model_name='machinerequest', name='parent_machine_tmp', field=models.ForeignKey(
                                                                                                                                            related_name='ancestor_machine', to='core.ProviderMachineTmp', null=True), preserve_default=True, ), migrations.AddField(
                                                                                                                                                model_name='providermachinemembership', name='provider_machine_tmp', field=models.ForeignKey(
                                                                                                                                                    to='core.ProviderMachineTmp', null=True), preserve_default=True, ), migrations.AddField(
                                                                                                                                                        model_name='volumestatushistory', name='volume_tmp', field=models.ForeignKey(
                                                                                                                                                            to='core.VolumeTmp', null=True), preserve_default=True, ), migrations.RunPython(
                                                                                                                                                                copy_data_to_new_models, do_nothing)]
