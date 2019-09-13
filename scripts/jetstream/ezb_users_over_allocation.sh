#!/usr/bin/env bash

echo "# EZ Button users over threshold (2K SU)"
echo ""

WEEK_AGO=$(date --date='a week ago' +%F)
. /opt/env/atmo/bin/activate
cd /opt/dev/atmosphere
cat scripts/jetstream/ezb_users_over_allocation.sql | sed "s/2017-12-01/${WEEK_AGO}/" | ./manage.py dbshell
