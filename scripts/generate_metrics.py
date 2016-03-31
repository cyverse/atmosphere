#!/usr/bin/env python
"""
This script is for the accounting purposes of Jetstream
The goal:
    Print a CSV of:
<instance_id>,<featured_image_name>,<went_active>,<went_deploy_error>,<went_error>
"""
import django; django.setup()
from core.models import Provider, Instance, InstanceStatusHistory

for inst in Instance.objects.order_by('-id'):
    first_history = inst.get_first_history()
    image_name = inst.source.providermachine.application_version.application.name
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
    hit_active = 1 if hit_active else 0
    hit_error = 1 if hit_error else 0
    hit_deploy_error = 1 if hit_deploy_error else 0
    arg_list = [inst.id, image_name, hit_active, hit_deploy_error, hit_error]
    print ",".join(map(str,arg_list))

