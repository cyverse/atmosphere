#!/usr/bin/env python
import argparse

import django; django.setup()

from core.models import Application, AtmosphereUser, MachineRequest
from service.driver import get_account_driver
from core.query import only_current_apps


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="List of provider names and IDs")
    args = parser.parse_args()
    admin_owned_apps = Application.objects.filter(
        created_by__username__contains='admin').filter(only_current_apps()).distinct()
    account_drivers = {}
    # FIXME: Change the provider_id if necessary.
    for app in admin_owned_apps:
        # Step 1 - See if MachineRequest can answer the question
        machine = app._current_machines().filter(instance_source__provider__id=4).first()
        if not machine:
            continue
        mr = MachineRequest.objects.filter(new_machine=machine).first()
        if mr:
            fix_application_owner(app, mr.created_by, args.dry_run)
            continue
        # Step 2 - See if glance can answer the question
        provider = machine.provider
        if account_drivers.get(provider):
            accounts = account_drivers[provider]
        else:
            accounts = get_account_driver(provider)
            account_drivers[provider] = accounts
        img = accounts.get_image(machine.identifier)
        if not img:
            continue
        project = accounts.get_project_by_id(img.owner)
        if not project:
            continue
        user = AtmosphereUser.objects.filter(username=project.name).first()
        if user:
            fix_application_owner(app, user, args.dry_run)



def fix_application_owner(app, user, dry_run=False):
    print "Application %s(%s) owned by %s" % (app.id, app.name, user)
    if dry_run:
        return
    app.created_by = user
    print "Fixed"


if __name__ == "__main__":
    main()
