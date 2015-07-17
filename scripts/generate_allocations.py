#!/usr/bin/env python
import argparse
from core.models import Provider, Identity
from service.monitoring import _get_allocation_result
import django
django.setup()


def main():
    """
    Return a list of ALL users on a provider, their CURRENT allocation totals,
    and # of instances used.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider-list", action="store_true",
                        help="List of provider names and IDs")
    parser.add_argument("--provider-id", type=int,
                        help="Atmosphere provider ID"
                        " to use when importing users.")
    parser.add_argument(
        "--users",
        help="list of usernames to generate allocations for.. (comma separated)")
    args = parser.parse_args()
    return run_command(args)


def provider_list():
    print "ID\tName"
    for p in Provider.objects.all().order_by('id'):
        print "%d\t%s" % (p.id, p.location)
    return None


def run_command(args):

    if args.provider_list:
        return provider_list()

    if not args.provider_id:
        print "ERROR: provider-id is required. To get a list of providers use"\
            " --provider-list"
        return -1
    provider = Provider.objects.get(id=args.provider_id)
    print "Provider Selected:%s" % provider

    users = args.users.split(",") if args.users else []
    if not users:
        idents = [ident for ident in
                  provider.identity_set.distinct('created_by')]
        users = [ident.created_by.username for ident in idents]
    else:
        idents = [
            Identity.objects.filter(
                created_by__username=user, provider=provider)[0]
            for user in users]
    # Sorting makes life easier
    idents = sorted(idents, key=lambda ident: ident.created_by.username)
    users = sorted(users)
    print "Users Selected:%s" % users
    return check_allocation_for(provider, idents)


def check_allocation_for(provider, idents):
    """
    Get the entire list first then print it all
    """
    results = _get_results(idents)
    print "Username, AU Allowed, AU  Used, AU Burn Rate,"\
        " Instance(s) Contributing to BurnRate"
    for ident, result in results:
        credit_hours = result.total_credit().total_seconds() / 3600
        if credit_hours > 240000000:
            credit_hours = 'Unlimited'
        runtime_hours = result.total_runtime().total_seconds() / 3600
        print "%s, %s AU, %s AU, %s AU per Hour," % (
            ident.created_by.username,
            credit_hours, runtime_hours,
            result.get_burn_rate() * 3600),
        for instance in result.allocation.instances:
            if len(instance.history) == 0:
                continue
            if not instance.history[-1].end_date:
                print "%s:%s - %s CPU, " % (instance.identifier[:5],
                                            instance.history[-1].status,
                                            instance.history[-1].size.cpu),
        print ""
    return results


def _get_results(idents):
    results = []
    total = len(idents)
    for idx, ident in enumerate(idents):
        try:
            result = _get_allocation_result(ident)
            results.append((ident, result))
        except Exception as exc:
            print "Error calculating for identity: %s" % ident
            print exc

        if total > 10 and idx % int(total / 10) == 0:
            print "Calculating %s/%s.." % (idx, total)
    return results

if __name__ == "__main__":
    main()
