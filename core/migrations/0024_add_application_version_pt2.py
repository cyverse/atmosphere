# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.utils.timezone
from django.conf import settings
import uuid
import json

VERBOSE = False


def migrate_to_new_fields(apps, schema_editor):
    Application = apps.get_model("core", "Application")
    ApplicationThreshold = apps.get_model("core", "ApplicationThreshold")
    ApplicationVersion = apps.get_model("core", "ApplicationVersion")
    ApplicationVersionMembership = apps.get_model(
        "core",
        "ApplicationVersionMembership")
    Group = apps.get_model("core", "Group")
    MachineRequest = apps.get_model("core", "MachineRequest")
    ProviderMachine = apps.get_model("core", "ProviderMachine")
    ProviderMachineMembership = apps.get_model(
        "core",
        "ProviderMachineMembership")
    update_application_versions(
        ProviderMachine,
        ProviderMachineMembership,
        ApplicationVersion,
        ApplicationVersionMembership,
        Application)
    update_machine_requests(
        MachineRequest,
        Group,
        ApplicationVersion,
        ApplicationThreshold)
    pass


def update_machine_requests(
        MachineRequest,
        Group,
        ApplicationVersion,
        ApplicationThreshold):
    for request in MachineRequest.objects.order_by('id'):
        update_machine_request(
            request,
            Group,
            MachineRequest,
            ApplicationVersion)

    for threshold in ApplicationThreshold.objects.order_by('id'):
        threshold.application_version = threshold.application.versions.last()
        threshold.save()


def _update_request(machine_request, Group):
    if machine_request.new_machine:
        current_version = machine_request.new_machine.application_version
        machine_request.new_application_version = current_version
    machine_request.new_application_visibility = machine_request.new_machine_visibility
    machine_request.new_version_name = machine_request.new_machine_version
    machine_request.new_application_name = machine_request.new_machine_name
    machine_request.new_version_tags = machine_request.new_machine_tags
    machine_request.new_application_description = machine_request.new_machine_description
    machine_request.new_version_change_log = machine_request.new_machine_description
    if machine_request.access_list:
        if '[' in machine_request.access_list:
            list_str = machine_request.access_list.replace(
                "'",
                '"').replace(
                'u"',
                '"')
            usernames = json.loads(list_str)
        else:
            usernames = machine_request.access_list.split(',')
        for name in usernames:
            try:
                name = name.strip()
                group = Group.objects.get(name=name)
                machine_request.new_version_membership.add(group)
            except Group.DoesNotExist:
                print 'Skipped user %s on request %s - DoesNotExist' % (name, machine_request.id)
    machine_request.save()


def update_machine_request(
        machine_request,
        Group,
        MachineRequest,
        ApplicationVersion):
    # Update the request
    _update_request(machine_request, Group)
    # Update the version
    _fill_version_using_machine_request(machine_request, ApplicationVersion)


def _many_to_many_copy(machine_manager, version_manager):
    if not machine_manager.count():
        return
    for x in machine_manager.order_by('id'):
        version_manager.add(x)


def _fill_version_using_machine_request(machine_request, ApplicationVersion):
    current_version = None
    if machine_request.new_machine:
        current_version = machine_request.new_machine.application_version

    parent_instance = machine_request.instance
    parent_version = parent_instance.source.providermachine.application_version

    if not current_version:
        return
    if not current_version.parent:
        current_version.parent = ApplicationVersion.objects.get(
            id=parent_version.id)
    # Double-check this..
    if not current_version.parent:
        print "WARN: Could not set fork version for MachineRequest %s." % machine_request.id

    current_version.change_log = machine_request.new_version_change_log
    current_version.allow_imaging = machine_request.new_version_allow_imaging

    current_version.iplant_system_files = machine_request.iplant_sys_files
    current_version.installed_software = machine_request.installed_software
    current_version.exclude_files = machine_request.exclude_files
    current_version.save()


def update_application_versions(
        ProviderMachine,
        ProviderMachineMembership,
        ApplicationVersion,
        ApplicationVersionMembership,
        Application):
    machines = ProviderMachine.objects.all()
    create_count = 0
    for machine in machines:
        created = update_application_version(
            machine,
            ApplicationVersion,
            ApplicationVersionMembership,
            ProviderMachineMembership)
        create_count += created
    # NOTE: comma at the end to intentionally leave all text on one line.
    # print "Converted %s ProviderMachines into %s ApplicationVersions on %s applications" % (ProviderMachine.objects.count(), ApplicationVersion.objects.count(), Application.objects.count()),


def update_application_version(
        machine,
        ApplicationVersion,
        ApplicationVersionMembership,
        ProviderMachineMembership):
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
    if (not app_version.end_date and source.end_date) or (
            app_version.end_date and source.end_date and app_version.end_date < source.end_date):
        app_version.end_date = source.end_date
    app_version.save()
    # Update machine association
    machine.application_version = app_version
    machine.save()
    # Save remaining associations
    if machine.licenses.count():
        for license in machine.licenses.all():
            app_version.licenses.add(license)
    machine_members = ProviderMachineMembership.objects.filter(
        provider_machine__id=machine.id)
    if machine_members.count():
        for pm_membership in machine_members:
            membership, _ = ApplicationVersionMembership.objects.get_or_create(
                application_version_id=app_version.id,
                group_id=pm_membership.group.id,
                can_share=pm_membership.can_share)
    return 1 if created else 0


def do_nothing(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0023_add_application_version'),
    ]

    operations = [
        migrations.RunPython(
            migrate_to_new_fields,
            migrations.RunPython.noop
        ),
    ]
