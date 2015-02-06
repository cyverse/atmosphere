#!/usr/bin/env python
# Takes a single command-line argument, a .json file generated from `./manage.py dumpdata service_old.machine &> machines.json`
import sys
import json
from datetime import datetime

from core.models import AtmosphereUser as User

from pytz import timezone

from core.models import IdentityMembership, Quota, Provider
import django
django.setup()

def get_unique_quota(old_list):
    d = {}
    for quota_obj in old_list:
        q = quota_obj['fields']
        mem_gb = q['memory']/1024
        if d.has_key( (q['cpu'],mem_gb) ):
            d[ (q['cpu'],mem_gb) ].append(q['userid'])
        else:
            d[ (q['cpu'],mem_gb) ] = [q['userid']]
    return d

def main(filename):
    f = open(filename, 'r')
    contents = f.read()
    f.close()
    old_quota = json.loads(contents)
    unique_quota = get_unique_quota(old_quota)
    euca = Provider.objects.get(location="EUCALYPTUS")
    failed = 0
    for ( (cpu,mem), users) in unique_quota.items():
        print cpu, mem
        print users
        new_quota_obj = Quota.objects.get_or_create(cpu=cpu,memory=mem)[0]
        for user in users:
            try:
                user_identity = IdentityMembership.objects.get(member__name=user, identity__provider=euca)
                user_identity.quota = new_quota_obj
                user_identity.save()
            except IdentityMembership.DoesNotExist, no_membership:
                print "Username: %s does not have an identity. Run scripts/import_users.py FIRST, then run scripts/import_quota.py" % user
                failed += 1
    print str(len(old_quota)-failed) + " quotas added"

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print "Usage: import_quota.py old_quota.json"
        sys.exit(1)
    main(sys.argv[1])
