#!/usr/bin/env python
import argparse
import os, traceback
import sys, time
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, root_dir)
os.environ["DJANGO_SETTINGS_MODULE"] = "atmosphere.settings"

import django; django.setup()

import libcloud.security

from django.db.models import Count, Q
from core.models import AtmosphereUser as User
from core.models import Provider, ProviderMachine, Size, InstanceSource
from core.query import only_current, only_current_source

from service.instance import launch_instance


libcloud.security.VERIFY_SSL_CERT = False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", help="The OpenStack compute node to launch"
                        " instances on.")
    parser.add_argument("--name",
                        help="The OpenStack compute node to launch"
                        " instances on.")
    parser.add_argument("--provider-list", action="store_true",
                        help="List of provider names and IDs")
    parser.add_argument("--provider-id", type=int, help="Atmosphere provider"
                        " to use when launching instances.")
    parser.add_argument("--machine-alias", help="Atmosphere machine alias,"
                        " or list of machine_alias separated by comma,"
                        " to use when launching instances.")
    parser.add_argument("--machine-list", action="store_true",
                        help="Return a list of machines"
                        " ordered by most launched instances"
                        " that have reached active state.")
    parser.add_argument("--size", help="Atmosphere size to use when"
                        " launching instances.")
    parser.add_argument("--size-list", action="store_true",
                        help="List of size names and IDs")
    parser.add_argument("--skip-deploy", action="store_true",
                        help="Don't run Atmosphere's deploy.")
    parser.add_argument("--count", default=1, type=int,
                        help="Number of instances to launch.")
    parser.add_argument("--users", help="Atmosphere usernames to launch with, in a comma-separated-list.")
    args = parser.parse_args()
    if args.provider_list:
        handle_provider_list()
        if not args.provider_id:
            sys.exit(0)
    handle_provider(args)
    provider = Provider.objects.get(id=args.provider_id)

    if args.machine_list:
        print_most_used(provider)
        sys.exit(1)

    if args.size_list:
        print "ID\tName\tCPU\tMemory"
        for s in Size.objects.filter(only_current(),
                                     provider=provider).order_by('id'):
            print "%s\t%s\t%d\t%d" % (s.id, s.name, s.cpu, s.mem)
        sys.exit(0)

    handle_size(args, provider)
    try:
        size_id = int(args.size)
        query = Q(id=size_id)
    except ValueError:  # Happens when type == str
        query = Q(name=args.size)

    size = Size.objects.get(query, only_current(), provider=provider)
    machines = handle_machine(args, provider)
    user_list = args.users.split(',')
    for idx, username in enumerate(user_list):
        try:
            if idx != 0:
                print "Sleep 30 seconds"
                time.sleep(30)
                print "Awake, ready to launch"
            launch_instance_for_user(args, machines, size, provider, username)
        except Exception as e:
            print "Instance launch *FAILED*: %s" % e
            traceback.print_exc(file=sys.stdout)


def launch_instance_for_user(args, machines, size, provider, username):
    print "Using Username %s." % username
    user = User.objects.get(username=username)
    handle_count(args)
    print "Using Provider %s." % provider
    print "Using Size %s." % size.name
    if args.host:
        host = "nova:%s" % args.host
    else:
        host = None
    if args.name:
        name = args.name
    else:
        name = None
    instances = launch(user, name, provider, machines, size,
           host, args.skip_deploy, args.count)
    print "Launched %d instances." % len(instances)


def handle_provider_list():
    print "ID\tName"
    for p in Provider.objects.all().order_by('id'):
        print "%d\t%s" % (p.id, p.location)


def handle_provider(args):
    if not args.provider_id:
        print "Error: provider-id is required. To get a list of providers"\
            " use --provider-list."
        sys.exit(1)

def sort_most_used_machines(provider, limit=0, offset=0):
    results = ProviderMachine.objects.none()
    query = InstanceSource.objects.filter(provider__id=4)\
           .filter(providermachine__isnull=False)\
           .filter(instances__instancestatushistory__status__name='active').distinct()\
           .annotate(instance_count=Count('instances'))\
           .order_by('-instance_count')
    if limit != 0:
        query = query[offset:offset+limit]
    for source in query:
        machine_alias = source.identifier
        results |= ProviderMachine.objects.filter(
            instance_source__identifier=machine_alias,
            instance_source__provider_id=provider.id).annotate(instance_count=Count('instance_source__instances'))
    return results

def print_most_used(provider):
    machines = sort_most_used_machines(provider, limit=16)
    machines = machines.annotate(inst_count=Count('instance_source__instances'))
    for result in machines:
        print "Instances Launched: %s - %s" % (result.inst_count, result)

def handle_machine(args, provider):
    if not args.machine_alias:
        print "Error: A machine-alias is required."
        sys.exit(1)
    if args.machine_alias == 'all':
        return ProviderMachine.objects.filter(
            only_current_source(),
            instance_source__provider_id=provider.id,
            ).distinct()
    elif args.machine_alias == 'most_used':
        return sort_most_used_machines(provider, limit=20)
    elif ',' not in args.machine_alias:
        return [ProviderMachine.objects.get(
            instance_source__identifier=args.machine_alias,
            instance_source__provider_id=provider.id)]
    else:
        machines = args.machine_alias.split(",")
        print "Batch launch of images detected: %s" % machines
        return [
            ProviderMachine.objects.get(
                instance_source__identifier=machine_alias,
                instance_source__provider_id=provider.id)
            for machine_alias in machines]


def handle_size(args, provider):
    if not args.size:
        print "Error: size name-or-id is required. To get a list of sizes"\
            " use --size-list."
        sys.exit(1)


def handle_count(args):
    if args.count < 1 or args.count > 10:
        print "Error: Count must be between 1 and 10."
        sys.exit(1)


def launch(user, name_prefix, provider, machines, size,
           host, skip_deploy, count):
    ident = user.identity_set.get(provider_id=provider.id)
    instances = []
    kwargs = {}
    if host:
        kwargs['ex_availability_zone'] = host
    machine_count = 0
    for c in range(0, count):
        for machine in machines:
            machine_count += 1
            gen_name = "%s v.%s" % (machine.application.name, machine.application_version.name)
            if name_prefix:
                name = "%s %s" % (name_prefix, machine_count)
            else:
                name = "%s %s" % (gen_name, machine_count)
            try:
                instance_id = launch_instance(
                    user, ident.uuid, size.alias,
                    machine.instance_source.identifier,
                    name=name,
                    deploy=(not skip_deploy),
                    **kwargs)
                print "Successfully launched Machine %s : %s" \
                    % (machine.instance_source.identifier, instance_id)
                instances.append(instance_id)
            except Exception as exc:
                print "Error on launch of Machine %s : %s" \
                      % (machine.instance_source.identifier, exc)
    return instances


if __name__ == "__main__":
    main()
