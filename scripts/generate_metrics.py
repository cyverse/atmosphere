#!/usr/bin/env python
"""
This script is for the accounting purposes of Jetstream
The goal:
    Print a CSV of:
"""
CSV_HEADER="Instance ID, Instance Alias, Username, Provider, Instance Start Date, Image Name, Version Name, Featured Image, Active, Deploy Error, Error, Aborted"

import django; django.setup()
from core.models import Provider, Instance, InstanceStatusHistory, ObjectDoesNotExist

print CSV_HEADER
inst_list = Instance.objects.all()
#inst_list = Instance.objects.filter(source__providermachine__application_version__application__tags__name__icontains='featured')
for inst in inst_list.order_by('id'):
    first_history = inst.get_first_history()
    try:
        instance_id = inst.provider_alias
        username = inst.created_by.username
        machine = inst.source.providermachine
        application_version = machine.application_version
        application = application_version.application
        provider = machine.provider.location
        image_name = application.name
        version_name = application_version.name
        featured_image = application.tags.filter(name__icontains='featured').count() > 0
    except ObjectDoesNotExist:
        image_name = "Deleted Image"
        version_name = "N/A"
        featured_image = False
    last_history = inst.get_last_history()
    history = first_history
    hit_aborted = hit_active = hit_deploy_error = hit_error = False
    while True:
        try:
            #print history.instance.id, history.status, history.start_date
            hit_active = hit_active or (history.status.name.lower() == 'active')
            hit_error = hit_error or (history.status.name.lower() == 'error')
            hit_deploy_error = hit_deploy_error or (history.status.name.lower() == 'deploy_error')
            history = history.next()
        except LookupError:
            break
        except ValueError:
            #NOTE: These value-errors are important debugging tools. but they can be ignored if you aren't hunting down problems.
            #raise
            break
    if not hit_active and not hit_error and not hit_deploy_error:
        hit_aborted = True
    featured_image = 1 if featured_image else 0
    #Magic goes here.
    if hit_active:
        hit_error = 0
        hit_deploy_error = 0
    if hit_error and hit_deploy_error:
        hit_error = 0
    #
    hit_active = 1 if hit_active else 0
    hit_aborted = 1 if hit_aborted else 0
    hit_error = 1 if hit_error else 0
    hit_deploy_error = 1 if hit_deploy_error else 0
    arg_list = [inst.id, instance_id, username, provider, inst.start_date.strftime("%x %X"), image_name, version_name, featured_image, hit_active, hit_deploy_error, hit_error, hit_aborted]
    print ",".join(map(str,arg_list))

