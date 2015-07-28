#!/usr/bin/env python
import argparse
import subprocess
import logging

from django.utils.timezone import datetime, utc
from service.driver import get_account_driver
from core.models import Provider, ProviderMachine, Identity, MachineRequest, Application, ProviderMachine
from core.models.application import _generate_app_uuid

Force = False

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true",
                        help="Force-repair requests that appear to be 'OK'")
    parser.add_argument("--provider", type=int,
                        help="Atmosphere provider ID"
                        " to use.")
    parser.add_argument("--request_ids", required=True,
                        help="Machine Request DB ID(s) to be repaired. (Comma-Separated)")

    args = parser.parse_args()
    if args.force:
        Force = True

    if not args.provider:
        provider = Provider.objects.get(location='iPlant Cloud - Tucson')
    else:
        provider = Provider.objects.get(id=args.provider)

    requests = args.request_ids.split(",")
    fix_requests(provider, requests)


def fix_requests(provider, requests=[]):
    accounts = get_account_driver(provider)
    for request_id in requests:
        try:
            machine_request = MachineRequest.objects.get(id=request_id)
        except MachineRequest.DoesNotExist:
            print "Warn: MachineRequest by this ID could not be found: %s" % request_id
            continue

        if machine_request.new_machine_provider != provider:
            raise ValueError("MachineRequest ID:%s is for Provider:%s. Testing Provider is:%s" % (request_id, machine_request.new_machine_provider, provider))
    fixed = False
    try:
        new_machine = ProviderMachine.objects.get(id=machine_request.new_machine_id)
    except ProviderMachine.DoesNotExist, no_match:
        print "OK: This MachineRequest has a BAD 'new_machine' (DoesNotExist)"
        new_machine = None
    if not fixed:
        fixed = _fix_wrong_machine_on_request(machine_request, provider, new_machine)
    if not fixed and new_machine:
        _fix_new_version_forked(machine_request, provider, new_machine)

def _fix_new_version_forked(machine_request, provider, new_machine):
    app_uuid = _generate_app_uuid(new_machine.identifier)
    if not machine_request.new_version_forked:
        return False
    if Application.objects.filter(uuid=app_uuid).count():
        return False
    print "OK: This MachineRequest: %s has a BAD Application." \
      "\tUUID should be %s." % (machine_request, app_uuid)
    old_application = new_machine.application
    current_application = _create_new_application(machine_request, new_machine.identifier)

    remaining_machines = old_application._current_machines()
    for machine in remaining_machines:
        if machine.identifier == new_machine.identifier:
            new_machine.application = current_application
            new_machine.save()
    current_application.save()
    # Pass #2 - If remaining, unmatched ids:
    remaining_machines = old_application._current_machines()

    acct_provider = machine_request.new_machine_provider
    accounts = get_account_driver(acct_provider)

    if remaining_machines:
        print "Warn: These machines likely point to the wrong application.:%s" % remaining_machines
        for machine in remaining_machines:
            glance_image = accounts.image_manager.get_image(machine.identifier)
            if glance_image:
                original_request = MachineRequest.objects.filter(new_application_name=glance_image.name)
                print "Hint: Image_ID:%s Named:%s MachineRequest:%s" % (glance_image.id, glance_image.name, original_request)

    return True

def _fix_wrong_machine_on_request(machine_request, provider, new_machine):
    if new_machine.provider == provider:
        return False
    print "OK: This MachineRequest: %s has a BAD 'new_machine':%s" \
      "\tProvider should be %s." % (machine_request, new_machine, provider)

    actual_image = _find_machine_by_request(machine_request)
    actual_machine = ProviderMachine.objects.get(identifier=actual_image.id, provider=provider)
    print "FIXED: Found correct 'new_machine': %s-->%s" % (new_machine, actual_machine)
    machine_request.new_machine = actual_machine
    machine_request.save()
    if 'ramdisk_id' not in actual_image.properties or 'kernel_id' not in actual_image.properties:
        print "WARN: Kernel/Ramdisk potentially missing. Run './scripts/repair_provider_machine.py --image_ids %s"\
            % (actual_image.id)


def _find_machine_by_request(machine_request):
    acct_provider = machine_request.new_machine_provider
    accounts = get_account_driver(acct_provider)
    images = accounts.list_all_images()

    lookup_name = machine_request.new_application_name
    started = machine_request.start_date
    completed = machine_request.end_date
    potential_matches = _match_by_date_range(images, started, completed)
    count = len(potential_matches)
    if count < 1:
        raise Exception("Could not find an image to match this MachineRequest!")
    elif count == 1:
        return potential_matches[0]
    else:
        return _match_by_name(potential_matches, lookup_name)

def _match_by_name(image_list, lookup_name):
    """
    Look for identically named machines
    Generally used AFTER _match_by_date_range (More Accurate)
    """
    matches = []
    for image in image_list:
        if image.name == lookup_name:
            matches.append(image)
    count = len(matches)
    if count < 1:
        raise Exception("Could not find an image named %s!" % lookup_name)
    elif count == 1:
        return matches[0]
    else:
        raise Exception("Ambiguity Error! Multiple images named %s: %s" % (lookup_name, matches))


def _match_by_date_range(image_list, started, completed):
    """
    Criteria for image we want to select:
        but created PRIOR to start date
        or created AFTER completion date
    """
    matches = []
    for image in image_list:
        image_date = _strptime(image.created_at)
        if image_date < started:
            continue
        if image_date > completed:
            continue
        # Falls within logical timespan. A potential match
        matches.append(image)
    return matches

def _strptime(timestamp):
    try:
        #99% of images use this Standard format
        return datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%S').replace(tzinfo=utc)
    except ValueError, bad_timestamp:
        if 'unconverted data' in bad_timstamp.message and 'Z' in bad_timestamp.message:
            #Include microseconds using ISO Standard
            return datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%S.%fZ').replace(tzinfo=utc)
        raise

def _create_new_application(machine_request, new_image_id, tags=[]):
    from core.models import Identity
    new_provider = machine_request.new_machine_provider
    user = machine_request.new_machine_owner
    owner_ident = Identity.objects.get(created_by=user, provider=new_provider)
    # This is a brand new app and a brand new providermachine
    new_app = create_application(
            new_image_id,
            new_provider.id,
            machine_request.new_application_name, 
            owner_ident,
            #new_app.Private = False when machine_request.is_public = True
            not machine_request.is_public(),
            machine_request.new_version_name,
            machine_request.new_application_description,
            tags)
    return new_app

def _update_parent_application(machine_request, new_image_id, tags=[]):
    parent_app = machine_request.instance.source.providermachine.application
    return _update_application(parent_app, machine_request, tags=tags)

def _update_application(application, machine_request, tags=[]):
    if application.name is not machine_request.new_application_name:
        application.name = machine_request.new_application_name
    if machine_request.new_application_description:
        application.description = machine_request.new_application_description
    application.private = not machine_request.is_public()
    application.tags = tags
    application.save()
    return application


if __name__ == "__main__":
    main()
