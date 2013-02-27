#!/usr/bin/env python
# Takes a single command-line argument, a .json file generated from `./manage.py dumpdata service_old.machine &> machines.json`
import sys
import json
from core.models import Machine, Provider, ProviderMachine
from django.contrib.auth.models import User
from datetime import datetime
from pytz import timezone


def convert_old_machine(machine_obj):
    old_machine = machine_obj['fields']
    print old_machine
    created_by = User.objects.filter(username=old_machine['image_ownerid'])
    if not created_by:
        created_by = User.objects.get(username='admin')
    else:
        created_by = created_by[0]
    #Do not add dummy images
    if not old_machine['image_name']:
        return (None,None)
    new_machine = {
        'name': old_machine['image_name'] if len(old_machine['image_name']) > 0 else old_machine['image_id'],
        'description': old_machine['image_description'] if old_machine['image_description'] else 'Describe %s' % old_machine['image_id'],
        'icon': None, #old_machine['machine_image'],
        'private': old_machine['image_is_public'] == 'private',
        'featured': old_machine['image_featured'],
        'created_by': created_by,
        'start_date': old_machine['registered_at'],
        'end_date': old_machine['image_end_date'],
    }
    new_provider_machine = {
        'identifier': old_machine['image_id']
    }
    return (new_machine, new_provider_machine)

def format_date(date_str):
    if not date_str:
        return None
    try:
        new_date = datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S')
    except ValueError, bad_format:
        new_date = datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S.%f')
    new_date = new_date.replace(tzinfo=timezone('UTC'))
    return new_date

def update_provider_machine(provider_machine, machine_obj):
    machine = provider_machine.machine
    machine.name = machine_obj['name']
    machine.description = machine_obj['description']
    machine.start_date = format_date(machine_obj['start_date'])
    machine.end_date = format_date(machine_obj['end_date'])
    machine.featured = machine_obj['featured']
    machine.private = machine_obj['private']
    machine.save()
    if machine.featured:
        print machine

def main(filename):
    f = open(filename, 'r')
    contents = f.read()
    old_machines = json.loads(contents)
    new_machines = map(convert_old_machine, old_machines)
    # new_machines is now a list of two-tuples of the form (core.models.Machine, core.models.ProviderMachine)

    euca = Provider.objects.get(location="EUCALYPTUS")

    for (machine_dict, provider_machine_dict) in new_machines:
        #Does the ProviderMachine exist?
        if not machine_dict or not provider_machine_dict:
            continue
        print machine_dict, provider_machine_dict
        provider_machine = ProviderMachine.objects.filter(identifier=provider_machine_dict['identifier'])
        if provider_machine:
            update_provider_machine(provider_machine[0], machine_dict)
        else:
            machine = Machine(**machine_dict)
            machine.save()
            provider_machine_dict['provider'] = euca
            provider_machine_dict['machine'] = machine
            provider_machine = ProviderMachine(**provider_machine_dict)
            provider_machine.save()

    print str(len(new_machines)) + " machines added"

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print "Usage: import_machines.py machines_old.json"
        sys.exit(1)
    main(sys.argv[1])
