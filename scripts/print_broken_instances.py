import django; django.setup()

from core.models import *

#
# Print a list of instances stuck in deploy_error or networking, that have
# never reached active
#

instances = []
for inst in Instance.objects.filter(end_date=None):
    statuses = inst.instancestatushistory_set
    last_status = statuses.last()

    # Instance is either in deploy_error or networking
    if last_status.status.name in ["deploy_error", "networking"]:

        # Instance never went active
        if not statuses.filter(status__name="active").exists():
            instances.append(inst)


print "UUID, PROVIDER, START_DATE, LAST_STATUS, USERNAME"
for inst in instances:
    uuid = inst.provider_alias
    provider = inst.provider.location
    start_date = str(inst.start_date)
    last_status = inst.instancestatushistory_set.last().status.name
    username = inst.created_by.username

    print ",".join([uuid, provider, start_date, last_status, username])
