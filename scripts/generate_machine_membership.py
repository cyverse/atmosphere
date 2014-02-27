#!/usr/bin/env python
from core.models import MachineRequest, Provider, ProviderMachine,\
        ProviderMachineMembership
from core.models.credential import get_groups_using_credential
from service.accounts.openstack import AccountDriver as OSAccounts
from service.driver import get_admin_driver
from api.machine import list_filtered_machines
from django.db.models import Q
from django.utils import timezone
import json

def parse_list(raw_access_list, provider_id):
    json_loads_list = raw_access_list.replace("'",'"').replace('u"', '"')
    user_list = json.loads(json_loads_list)
    return user_list


def main():
    providers = Provider.objects.filter(
            Q(type__name__iexact="openstack") &
            Q(active=True) & 
            (Q(end_date=None) | Q(end_date__gt=timezone.now())))
    for prov in providers:
        accounts = OSAccounts(prov)
        if not accounts:
            print "Aborting import: Could not retrieve OSAccounts driver for Provider %s" % p
            continue
        admin_driver = get_admin_driver(prov)
        if not admin_driver:
            print "Aborting import: Could not retrieve admin_driver for Provider %s" % p
            continue
        requests = MachineRequest.objects.filter(
            Q(new_machine_provider=prov) &
            ~Q(new_machine_visibility__exact="public") &
            Q(new_machine__isnull=False))
        for mr in requests:
            user_list  = parse_list(mr.access_list, prov.id)
            image = accounts.image_manager.get_image(mr.new_machine.identifier)
            print "Adding membership for %s users on image %s<%s>" \
                    % (len(user_list), image.id, image.name)
            for tenant_name in user_list:
                try:
                    accounts.image_manager.share_image(image, tenant_name)
                    print "%s has permission to launch %s" % (tenant_name, image)
                except Exception as e:
                    print "Failed to share image with tenant_name=%s" \
                            % (tenant_name)
                    continue
                pm = ProviderMachine.objects.filter(provider=prov,
                                                    identifier=image.id)
                if not pm:
                    continue
                pm = pm[0]
                affected_membership = get_groups_using_credential(
                        "ex_project_name", tenant_name, prov)
                for affected_member in affected_membership:
                    obj, created = ProviderMachineMembership.objects.get_or_create(
                            group=affected_member.member, 
                            provider_machine=pm)
                    if created:
                        print "Created new ProviderMachineMembership: %s" % obj

if __name__ == "__main__":
    main()

