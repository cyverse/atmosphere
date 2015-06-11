# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


def copy_data_to_models(apps, schema_editor):
    MachineRequest = apps.get_model("core", "MachineRequest")
    ApplicationVersion = apps.get_model("core", "ApplicationVersion")
    ApplicationThreshold = apps.get_model("core", "ApplicationThreshold")
    for request in MachineRequest.objects.order_by('id'):
        update_machine_request(request, MachineRequest)

    for threshold in ApplicationThreshold.objects.order_by('id'):
        threshold.application_version = threshold.application.versions.last()
        threshold.save()


def update_machine_request(request, MachineRequest):
    #if request.new_machine_forked:
    #    # Specific to Created applications
    #    request.new_application_name = request.new_machine_name
    #    pass
    #else:
    #    # Specific to Updated applications
    #    request.new_application_name = None
    #if request.new_machine:
    #    request.new_application_version = request.new_machine.application_version

    #request.new_version_allow_imaging = request.new_machine_allow_imaging
    #request.new_version_description = request.new_machine_description
    #request.new_version_forked = request.new_machine_forked
    #request.new_version_memory_min = request.new_machine_memory_min
    #request.new_version_storage_min = request.new_machine_storage_min
    #request.new_version_visibility = request.new_machine_visibility
    request.save()
    _fill_version_using_machine_request(request)
    _many_to_many_copy(request.new_machine_licenses, request.new_version_licenses)
    #Update the request


def _many_to_many_copy(machine_manager, version_manager):
    if not machine_manager.count():
        return
    for x in machine_manager.order_by('id'):
        version_manager.add(x)

def _fill_version_using_machine_request(machine_request):
    if not machine_request.new_application_version:
        return

    current_version = machine_request.new_application_version
    parent_instance = machine_request.instance
    parent_version = parent_instance.source.providermachine.application_version

    if not current_version.fork_version:
        if parent_version:
            current_version.fork_version = parent_version
        else:
            print "WARN: Could not set fork version for MachineRequest %s." % machine_request.id
    current_version.description = machine_request.new_version_description
    current_version.allow_imaging = machine_request.new_version_allow_imaging

    current_version.iplant_system_files = machine_request.iplant_sys_files
    current_version.installed_software = machine_request.installed_software
    current_version.exclude_files = machine_request.exclude_files
    current_version.save()


def do_nothing(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0024_add_fields_machine_request_and_version'),
    ]

    operations = [
        migrations.RunPython(
            copy_data_to_models, do_nothing),
    ]
