# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.utils.timezone
from django.conf import settings
import uuid

VERBOSE = False

def migrate_to_new_fields(apps, schema_editor):
    Application = apps.get_model("core", "Application")
    ApplicationThreshold = apps.get_model("core", "ApplicationThreshold")
    ApplicationVersion = apps.get_model("core", "ApplicationVersion")
    ApplicationVersionMembership = apps.get_model("core", "ApplicationVersionMembership")
    MachineRequest = apps.get_model("core", "MachineRequest")
    ProviderMachine = apps.get_model("core", "ProviderMachine")
    ProviderMachineMembership = apps.get_model("core", "ProviderMachineMembership")
    update_application_versions(ProviderMachine, ProviderMachineMembership, ApplicationVersion, ApplicationVersionMembership, Application)
    update_machine_requests(MachineRequest, ApplicationVersion, ApplicationThreshold)
    pass

def update_machine_requests(MachineRequest, ApplicationVersion, ApplicationThreshold):
    for request in MachineRequest.objects.order_by('id'):
        update_machine_request(request, MachineRequest, ApplicationVersion)

    for threshold in ApplicationThreshold.objects.order_by('id'):
        threshold.application_version = threshold.application.versions.last()
        threshold.save()


def update_machine_request(request, MachineRequest, ApplicationVersion):
    _fill_version_using_machine_request(request, ApplicationVersion)
    #Update the request


def _many_to_many_copy(machine_manager, version_manager):
    if not machine_manager.count():
        return
    for x in machine_manager.order_by('id'):
        version_manager.add(x)

def _fill_version_using_machine_request(machine_request, ApplicationVersion):
    current_version = None
    if machine_request.new_machine:
        current_version = machine_request.new_machine.application_version
        machine_request.new_application_version = current_version

    parent_instance = machine_request.instance
    parent_version = parent_instance.source.providermachine.application_version

    if not current_version:
        return
    if not current_version.parent:
        current_version.parent = ApplicationVersion.objects.get(id=parent_version.id)
    #Double-check this..
    if not current_version.parent:
        print "WARN: Could not set fork version for MachineRequest %s." % machine_request.id

    current_version.change_log = machine_request.new_version_change_log
    current_version.allow_imaging = machine_request.new_version_allow_imaging

    current_version.iplant_system_files = machine_request.iplant_sys_files
    current_version.installed_software = machine_request.installed_software
    current_version.exclude_files = machine_request.exclude_files
    current_version.save()


def update_application_versions(ProviderMachine, ProviderMachineMembership, ApplicationVersion, ApplicationVersionMembership, Application):
    machines = ProviderMachine.objects.all()
    create_count = 0
    for machine in machines:
        created = update_application_version(machine, ApplicationVersion, ApplicationVersionMembership, ProviderMachineMembership)
        create_count += created
    #NOTE: comma at the end to intentionally leave all text on one line.
    print "Converted %s ProviderMachines into %s ApplicationVersions on %s applications" % (ProviderMachine.objects.count(), ApplicationVersion.objects.count(), Application.objects.count()),

def update_application_version(machine, ApplicationVersion, ApplicationVersionMembership, ProviderMachineMembership):
    source = machine.instance_source
    app = machine.application
    if machine.version == '1.0.0':
        machine.version = '1.0'
    app_version, created = ApplicationVersion.objects.get_or_create(
            application=app,
            name=machine.version,
            created_by=app.created_by,
            created_by_identity=app.created_by_identity)
    if VERBOSE:
        print "ProviderMachine: %s+%s Version: %s "\
              "= ApplicationVersion %s for App %s (%s)" %\
              (source.provider.location, source.identifier, machine.version, app_version.id,
               app.name, app.uuid)
    if not machine.allow_imaging:
        app_version.allow_imaging = False
    if not app_version.start_date or app_version.start_date > source.start_date:
        app_version.start_date = source.start_date
    if (not app_version.end_date and source.end_date) or \
       (app_version.end_date and source.end_date and app_version.end_date < source.end_date):
        app_version.end_date = source.end_date
    app_version.save()
    #Update machine association
    machine.application_version = app_version
    machine.save()
    #Save remaining associations
    if machine.licenses.count():
        for license in machine.licenses.all():
            app_version.licenses.add(license)
    machine_members = ProviderMachineMembership.objects.filter(provider_machine__id=machine.id)
    if machine_members.count():
        for pm_membership in machine_members:
            membership, _ = ApplicationVersionMembership.objects.get_or_create(
                application_version_id = app_version.id,
                group_id = pm_membership.group.id,
                can_share = pm_membership.can_share)
    return 1 if created else 0

def do_nothing(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0022_remove_quota_and_allocation_request'),
    ]

    operations = [
        migrations.CreateModel(
            name='ApplicationVersion',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, serialize=False, editable=False, primary_key=True)),
                ('name', models.CharField(max_length=256)),
                ('change_log', models.TextField(null=True, blank=True)),
                ('allow_imaging', models.BooleanField(default=True)),
                ('start_date', models.DateTimeField(default=django.utils.timezone.now)),
                ('end_date', models.DateTimeField(null=True, blank=True)),
                ('iplant_system_files', models.TextField(default=b'', null=True, blank=True)),
                ('installed_software', models.TextField(default=b'', null=True, blank=True)),
                ('excluded_files', models.TextField(default=b'', null=True, blank=True)),
            ],
            options={
                'db_table': 'application_version',
            },
        ),
        migrations.CreateModel(
            name='ApplicationVersionMembership',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('can_share', models.BooleanField(default=False)),
                ('application_version', models.ForeignKey(to='core.ApplicationVersion')),
                ('group', models.ForeignKey(to='core.Group')),
            ],
            options={
                'db_table': 'application_version_membership',
            },
        ),
        migrations.RenameField(
            model_name='machinerequest',
            old_name='new_machine_allow_imaging',
            new_name='new_version_allow_imaging',
        ),
        migrations.RenameField(
            model_name='machinerequest',
            old_name='new_machine_forked',
            new_name='new_version_forked',
        ),
        migrations.RenameField(
            model_name='machinerequest',
            old_name='new_machine_licenses',
            new_name='new_version_licenses',
        ),
        migrations.RenameField(
            model_name='machinerequest',
            old_name='new_machine_memory_min',
            new_name='new_version_memory_min',
        ),
        migrations.RenameField(
            model_name='machinerequest',
            old_name='new_machine_storage_min',
            new_name='new_version_storage_min',
        ),
        migrations.AddField(
            model_name='machinerequest',
            name='new_application_description',
            field=models.TextField(default=b'', null=True, blank=True),
        ),
        migrations.AddField(
            model_name='machinerequest',
            name='new_application_name',
            field=models.CharField(max_length=256, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='machinerequest',
            name='new_application_visibility',
            field=models.CharField(max_length=256, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='machinerequest',
            name='new_version_change_log',
            field=models.TextField(default=b'', null=True, blank=True),
        ),
        migrations.AddField(
            model_name='machinerequest',
            name='new_version_membership',
            field=models.ManyToManyField(to='core.Group', blank=True),
        ),
        migrations.AddField(
            model_name='machinerequest',
            name='new_version_name',
            field=models.CharField(max_length=256, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='machinerequest',
            name='new_version_tags',
            field=models.TextField(default=b'', null=True, blank=True),
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
            name='status',
            field=models.TextField(default=b'', null=True, blank=True),
        ),
        migrations.AddField(
            model_name='applicationversion',
            name='application',
            field=models.ForeignKey(related_name='versions', to='core.Application'),
        ),
        migrations.AddField(
            model_name='applicationversion',
            name='created_by',
            field=models.ForeignKey(to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='applicationversion',
            name='created_by_identity',
            field=models.ForeignKey(to='core.Identity', null=True),
        ),
        migrations.AddField(
            model_name='applicationversion',
            name='parent',
            field=models.ForeignKey(to='core.ApplicationVersion', null=True, blank=True),
        ),
        migrations.AddField(
            model_name='applicationversion',
            name='licenses',
            field=models.ManyToManyField(related_name='application_versions', to='core.License', blank=True),
        ),
        migrations.AddField(
            model_name='applicationversion',
            name='membership',
            field=models.ManyToManyField(related_name='application_versions', through='core.ApplicationVersionMembership', to='core.Group', blank=True),
        ),
        migrations.AddField(
            model_name='applicationthreshold',
            name='application_version',
            field=models.OneToOneField(related_name='threshold', null=True, blank=True, to='core.ApplicationVersion'),
        ),
        migrations.AddField(
            model_name='machinerequest',
            name='new_application_version',
            field=models.ForeignKey(blank=True, to='core.ApplicationVersion', null=True),
        ),
        migrations.AddField(
            model_name='providermachine',
            name='application_version',
            field=models.ForeignKey(related_name='machines', to='core.ApplicationVersion', null=True),
        ),
        migrations.AlterUniqueTogether(
            name='applicationversionmembership',
            unique_together=set([('application_version', 'group')]),
        ),
        migrations.AlterUniqueTogether(
            name='applicationversion',
            unique_together=set([('application', 'name')]),
        ),
	# MIGRATE BEFORE REMOVAL
	migrations.RunPython(
	    migrate_to_new_fields,
	    do_nothing
	),
        migrations.RemoveField(
            model_name='applicationthreshold',
            name='application',
        ),
        migrations.RemoveField(
            model_name='machinerequest',
            name='new_machine_description',
        ),
        migrations.RemoveField(
            model_name='machinerequest',
            name='new_machine_name',
        ),
        migrations.RemoveField(
            model_name='machinerequest',
            name='new_machine_tags',
        ),
        migrations.RemoveField(
            model_name='machinerequest',
            name='new_machine_version',
        ),
        migrations.RemoveField(
            model_name='machinerequest',
            name='new_machine_visibility',
        ),
        migrations.RemoveField(
            model_name='providermachine',
            name='allow_imaging',
        ),
        migrations.RemoveField(
            model_name='providermachine',
            name='application',
        ),
        migrations.RemoveField(
            model_name='providermachine',
            name='licenses',
        ),
        migrations.RemoveField(
            model_name='providermachine',
            name='version',
        ),
    ]
