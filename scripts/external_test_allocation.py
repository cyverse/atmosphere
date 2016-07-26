#!/usr/bin/env python
from django import setup
setup()
from service.monitoring import get_allocation_result_for
from core.models import Identity, Instance, AtmosphereUser
from django.utils.timezone import timedelta, datetime
import pytz, sys
from dateutil.parser import parse

if len(sys.argv) < 3:
    print "Invalid # of args"
    print "Usage: %s <username> <start> <end>" % sys.argv[0]
    print "All times assumed to be in utc"
    sys.exit(1)

def utc_parse(date_str):
    dt = parse(date_str)
    return pytz.utc.localize(dt)

username=sys.argv[1]
start = utc_parse(sys.argv[2])
end = utc_parse(sys.argv[3])
print "Testing %s from %s - %s" % (username, start, end)
ident = Identity.objects.get(provider__id=4, created_by__username=username)
#import ipdb;ipdb.set_trace()
result = get_allocation_result_for(ident.provider, ident.created_by, True, start, end)
print result.allocation
print result
