#!/usr/bin/env python
import argparse
import subprocess
import logging

from django.utils.timezone import datetime, utc
from service.driver import get_account_driver
from core.models import Provider, ProviderMachine, Identity, MachineRequest, Application, ProviderMachine
from core.models.application import _generate_app_uuid
from core.models.machine_request import _update_application, _create_new_application

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
        try:
            new_machine = ProviderMachine.objects.get(id=machine_request.new_machine_id)
            if new_machine.provider == provider:
                if not Force:
                    print "OK: MachineRequest: %s 'new_machine' %s matches provider. use --force to continue fixing this request" % (machine_request, new_machine)
                    continue
            print "OK: This MachineRequest: %s has a BAD 'new_machine':%s" \
                  "\tProvider should be %s." % (machine_request, new_machine, provider)
        except ProviderMachine.DoesNotExist, no_match:
            print "OK: This MachineRequest has a BAD 'new_machine' (DoesNotExist)"
            new_machine = None
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

    lookup_name = machine_request.new_machine_name
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


if __name__ == "__main__":
    main()
