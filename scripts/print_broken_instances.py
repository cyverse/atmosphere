#!/usr/bin/env python
import argparse
import sys

def main():

    description = (
        "Print instances in deploy_error/networking that never "
        "went active"
    )

    parser = argparse.ArgumentParser(description=description)
    args = parser.parse_args()

    # Check environment
    try:
        import django; django.setup()
        from core.models import Instance
    except:
        print "\n".join([
            "ERROR! This script requires a proper environment! Try:",
            "",
            "   export PYTHONPATH=\"/opt/dev/atmosphere:$PYTHONPATH\"",
            "   export DJANGO_SETTINGS_MODULE='atmosphere.settings'",
            "   . /opt/env/atmo/bin/activate"
        ])
        sys.exit(1)


    # Filter instances
    instances = []
    for inst in Instance.objects.filter(end_date=None).order_by('start_date'):
        statuses = inst.instancestatushistory_set
        last_status = statuses.last()
        if last_status.status.name in ["error"]:
           instances.append(inst)
           continue

        # Instance is either in deploy_error or networking
        if last_status.status.name in ["deploy_error", "networking"]:

            # Instance never went active
            if not statuses.filter(status__name="active").exists():
                instances.append(inst)


    # Print csv
    print "UUID, PROVIDER, START_DATE, LAST_STATUS, USERNAME, EVER_HIT_ACTIVE?"
    for inst in instances:
        uuid = inst.provider_alias
        provider = inst.provider.location
        start_date = str(inst.start_date)
        last_status = inst.instancestatushistory_set.last().status.name
        ever_hit_active = inst.instancestatushistory_set.filter(status__name='active').count() > 0
        username = inst.created_by.username

        print ",".join([uuid, provider, start_date, last_status, username, str(ever_hit_active)])

if __name__ == "__main__":
    main()
