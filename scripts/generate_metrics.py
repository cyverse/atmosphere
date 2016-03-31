#!/usr/bin/env python
"""
This script is for the accounting purposes of Jetstream
The goal:
    Print a CSV of:
"""
CSV_HEADER="Instance ID, Instance Start Date, Image Name, Active, Deploy Error, Error"

import django; django.setup()
from core.models import Provider, Instance, InstanceStatusHistory, ObjectDoesNotExist

print CSV_HEADER
inst_list = Instance.objects.all()
inst_list = Instance.objects.filter(source__providermachine__application_version__application__tags__name__icontains='featured')
for inst in inst_list.order_by('id'):
    first_history = inst.get_first_history()
    try:
        application = inst.source.providermachine.application_version.application
        image_name = application.name
        featured_image = application.tags.filter(name__icontains='featured').count() > 0
    except ObjectDoesNotExist:
        image_name = "Deleted Image"
        featured_image = False
    last_history = inst.get_last_history()
    history = first_history
    hit_active = hit_deploy_error = hit_error = False
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
    featured_image = 1 if featured_image else 0
    #Magic goes here.
    if hit_active:
        hit_error = 0
        hit_deploy_error = 0
    if hit_error and hit_deploy_error:
        hit_error = 0
    #
    hit_active = 1 if hit_active else 0
    hit_error = 1 if hit_error else 0
    hit_deploy_error = 1 if hit_deploy_error else 0
    arg_list = [inst.id, inst.start_date.strftime("%x %X"), image_name, hit_active, hit_deploy_error, hit_error]
    print ",".join(map(str,arg_list))

