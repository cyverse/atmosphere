#!/usr/bin/env python
from collections import OrderedDict
import time

from api import get_esh_driver
from core.models import Provider, Identity
from service.driver import get_admin_driver
from service.instance import suspend_instance

def suspend_all_instances():
    admin_driver = get_admin_driver(Provider.objects.get(id=4))
    all_insts = admin_driver.meta(admin_driver=admin_driver).all_instances()
    users = []
    bad_instances = []
    for i in all_insts:
        if 'creator' in i.extra['metadata']:
            users.append(i.extra['metadata']['creator'])
        else:
            bad_instances.append(i)
    if bad_instances:
        print "WARN: These instances are MISSING because they have incomplete metadata:\n%s" % (bad_instances,)
    all_users = sorted(list(OrderedDict.fromkeys(users)))
    for count, user in enumerate(all_users):
        ident = Identity.objects.filter(created_by__username=user, provider__id=4)
        if len(ident) > 1:
            print "WARN: User %s has >1 identity!" % user
        ident = ident[0]
        driver = get_esh_driver(ident)
        instances = driver.list_instances()
        print "Found %s instances for %s" % (len(instances), user)
        for inst in instances:
            if inst._node.extra['status'] == 'active':
                print "Attempt to suspend Instance %s in state %s" % (inst.id, inst._node.extra['status'])
                try:
                    suspend_instance(driver, inst, ident.provider.id, ident.id, ident.created_by)
                    print "Suspended Instance %s.. Sleep 2min" % (inst.id,)
                    time.sleep(2*60)
                except Exception, err:
                    print "WARN: Could not suspend instance %s. Error: %s" % (inst.id, err)

if __name__ == "__main__":
    suspend_all_instances()
