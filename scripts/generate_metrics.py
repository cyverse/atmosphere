#!/usr/bin/env python
"""
This script is for the accounting purposes of Jetstream
The goal:
    Print a CSV of:
"""
CSV_HEADER="Instance ID, Instance Alias, Username, Staff_user, Provider, Instance Start Date, Image Name, Version Name, Size Name, Size Alias, Size cpu, Size mem, Size disk, Featured Image, Active, Deploy Error, Error, Aborted"
import sys
import django; django.setup()
from django.core.exceptions import MultipleObjectsReturned
from core.models import Provider, Instance, InstanceStatusHistory, ObjectDoesNotExist
from django.utils import timezone

time_start = timezone.now()
inst_list = Instance.objects.filter(created_by_identity__provider__id__in=[4,5,6])
count = inst_list.count()
#inst_list = Instance.objects.filter(source__providermachine__application_version__application__tags__name__icontains='featured')
print >> sys.stderr, "%s Begin processing %s records" % (timezone.now(), count)
print CSV_HEADER
content = ""
for idx, inst in enumerate(inst_list.order_by('id')):
    pct_value = round( float(idx*100)/count, 3)
    if pct_value % 5 == 0:
        print >> sys.stderr, "%s Percentage completed:%s" % (timezone.now(), pct_value)
        print content
        content = ""
    first_history = inst.get_first_history()
    try:
        instance_id = inst.provider_alias
        username = inst.created_by.username
        staff_user = inst.created_by.is_staff
        size = inst.get_size()
        machine = inst.source.providermachine
        application_version = machine.application_version
        application = application_version.application
        provider = machine.provider.location
        image_name = application.name.replace(",","-")
        version_name = application_version.name.replace(",","-")
        featured_image = application.tags.filter(name__icontains='featured').count() > 0
    except ObjectDoesNotExist:
        image_name = "Deleted Image"
        version_name = "N/A"
        featured_image = False
    hit_aborted = hit_active = hit_deploy_error = hit_error = False
    history = first_history

    hit_active = inst.instancestatushistory_set.filter(status__name='active').count() > 0
    hit_deploy_error = hit_active == False and inst.instancestatushistory_set.filter(status__name='deploy_error').count() > 0
    hit_error = hit_active == False and inst.instancestatushistory_set.filter(status__name='error').count() > 0
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
    arg_list = [inst.id, instance_id, username, staff_user, provider, inst.start_date.strftime("%x %X"), image_name, version_name, size.name, size.alias, size.cpu, size.mem, size.disk, featured_image, hit_active, hit_deploy_error, hit_error, hit_aborted]
    csv_line = ",".join(map(str,arg_list))
    content += "%s\n" % csv_line
time_duration = timezone.now() - time_start
print content
print "\n\nContent generated in %s" % time_duration
