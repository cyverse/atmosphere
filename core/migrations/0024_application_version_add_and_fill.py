# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.utils.timezone
import uuid

VERBOSE = False

def fill_with_data(apps, schema_editor):
    ProviderMachine = apps.get_model("core", "ProviderMachine")
    Application = apps.get_model("core", "Application")
    ApplicationVersion = apps.get_model("core", "ApplicationVersion")
    ApplicationVersionMembership = apps.get_model("core", "ApplicationVersionMembership")
    ProviderMachineMembership = apps.get_model("core", "ProviderMachineMembership")
    update_application_versions(ProviderMachine, ProviderMachineMembership, ApplicationVersion, ApplicationVersionMembership, Application)
    pass

def update_application_versions(ProviderMachine, ProviderMachineMembership, ApplicationVersion, ApplicationVersionMembership, Application):
    machines = ProviderMachine.objects.all()
    create_count = 0
    for machine in machines:
        created = update_application_version(machine, ApplicationVersion, ApplicationVersionMembership, ProviderMachineMembership)
        create_count += created
    print "Converted %s ProviderMachines into %s ApplicationVersions on %s applications" % (ProviderMachine.objects.count(), ApplicationVersion.objects.count(), Application.objects.count())

def update_application_version(machine, ApplicationVersion, ApplicationVersionMembership, ProviderMachineMembership):
    source = machine.instance_source
    app = machine.application
    if machine.version == '1.0.0':
        machine.version = '1.0'
    app_version, created = ApplicationVersion.objects.get_or_create(
            application=app,
            name=machine.version)
    if VERBOSE:
        print "ProviderMachine: %s+%s Version: %s "\
              "= ApplicationVersion %s for App %s (%s)" %\
              (source.provider.location, source.identifier, machine.version, app_version.id,
               app.name, app.uuid)
    app_version.description = app.description
    if not machine.allow_imaging:
        app_version.allow_imaging = False
    if not app_version.icon and app.icon:
        app_version.icon = app.icon
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
    if machine.members.count():
        for member in machine.members.all():
            pmm = ProviderMachineMembership.objects.get(
                group=member, provider_machine=machine)
            membership, _ = ApplicationVersionMembership.objects.get_or_create(
                application_version = app_version,
                group = pmm.group,
                can_share = pmm.can_share)
    return 1 if created else 0

def do_nothing(apps, schema_editor):
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0023_remove_redundant_fields_machine_request_and_version'),
    ]

    operations = [
        migrations.CreateModel(
            name='ApplicationVersion',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, serialize=False, editable=False, primary_key=True)),
                ('name', models.CharField(max_length=32, blank=True)),
                ('description', models.TextField(null=True, blank=True)),
                ('icon', models.ImageField(null=True, upload_to=b'application_versions', blank=True)),
                ('allow_imaging', models.BooleanField(default=True)),
                ('start_date', models.DateTimeField(default=django.utils.timezone.now)),
                ('end_date', models.DateTimeField(null=True, blank=True)),
                ('application', models.ForeignKey(to='core.Application')),
                ('fork_version', models.ForeignKey(to='core.ApplicationVersion', blank=True, null=True)),
                ('licenses', models.ManyToManyField(related_name='application_versions', to='core.License', blank=True)),
            ],
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
        migrations.AddField(
            model_name='applicationversion',
            name='membership',
            field=models.ManyToManyField(related_name='application_versions', through='core.ApplicationVersionMembership', to='core.Group', blank=True),
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
        migrations.RunPython(
            fill_with_data, do_nothing
        ),
        migrations.RemoveField(
            model_name='application',
            name='description',
        ),
        migrations.RemoveField(
        model_name='application',
            name='icon',
        ),
        migrations.RemoveField(
            model_name='providermachine',
            name='allow_imaging',
        ),
        migrations.RemoveField(
            model_name='providermachine',
            name='licenses',
        ),
        migrations.RemoveField(
            model_name='providermachine',
            name='version',
        ),
        migrations.RemoveField(
            model_name='providermachine',
            name='application',
        ),
        migrations.AlterField(
            model_name='applicationversion',
            name='application',
            field=models.ForeignKey(related_name='versions', to='core.Application'),
        ),
    ]
