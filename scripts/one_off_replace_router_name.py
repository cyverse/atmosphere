#!/usr/bin/env python
"""
This script will take all users without a 'router_name' credential in Identity and assign it to them.
Distribution will occur evenly across PUBLIC_ROUTERS, and take into account previously set router_names.
"""
import django; django.setup()
from django.db.models import Q
from atmosphere.settings import PUBLIC_ROUTERS
from core.models import Identity, Credential


def main():
    query = Q(credential__key='router_name')
    needs_router = Identity.objects.filter(~query)
    router_map = {entry: 0 for entry in PUBLIC_ROUTERS.split(',')}
    router_map = get_router_distribution(router_map)
    for identity in needs_router:
        selected_router = select_router(router_map)
        identity.credential_set.add(
            Credential(key='router_name', value=selected_router)
        )
        router_map[selected_router] += 1
    latest_router_map = get_router_distribution()
    return latest_router_map


def select_router(router_count_map):
    minimum = -1
    minimum_key = None
    for key, count in router_count_map.items():
        if minimum == -1:
            minimum = count
            minimum_key = key
        elif count < minimum:
            minimum = count
            minimum_key = key
    return minimum_key


def get_router_distribution(router_count_map={}):
    query = Q(credential__key='router_name')
    includes_router = Identity.objects.filter(query)
    for entry in includes_router.values_list('credential__value', flat=True):
        if entry in router_count_map:
            router_count_map[entry] = router_count_map[entry] + 1
        else:
            router_count_map[entry] = 1
    print "Current distribution of routers:"
    for entry, count in router_count_map.items():
        print "%s: %s" % (entry, count)
    return router_count_map


if __name__ == "__main__":
    main()
