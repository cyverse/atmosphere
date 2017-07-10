#!/usr/bin/env python
"""
This script can be used to query the Instance Reporting API without having to go through nginx/uwsgi
Instead, the script will create an API Factory with DRF, render the results via DRF,
and then offload all data into the specified file location.
"""
import argparse

import django; django.setup()
from django.conf import settings

from django.core.urlresolvers import reverse
from core.models import AtmosphereUser, Provider
from api.v2.views import ReportingViewSet
from rest_framework.test import APIRequestFactory, force_authenticate


def generate_report(username, start_date, end_date, provider_ids, file_location):
    reporting_url = reverse('api:v2:reporting-list')
    reporting_url += "?format=xlsx&start_date=2017-01-01&end_date=2017-07-01"
    for provider_id in provider_ids:
        reporting_url += "&provider_id="+provider_id
    view = ReportingViewSet.as_view({'get': 'list'})
    user = AtmosphereUser.objects.get(username='sgregory')
    factory = APIRequestFactory()
    request = factory.get(reporting_url)
    request.environ['SERVER_NAME'] = settings.SERVER_URL.replace("https://", "")
    force_authenticate(request, user=user)
    response = view(request)
    # Generate data into response here...
    with open(file_location, 'wb') as reporting_file:
        for chunk in response.rendered_content:
            reporting_file.write(chunk)
        reporting_file.flush()
    return file_location


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider-ids", required=True,
                        help="Atmosphere provider IDs"
                        " to get metrics from (Comma separated list)")
    parser.add_argument("--provider-list",
                        action="store_true",
                        help="List of provider names and IDs")
    parser.add_argument("--username", required=True,
                        help="Username to query the API with (Must be a staff user)")
    parser.add_argument("--start-date", required=True,
                        help="Formatted start date (YYYY-MM-DD) required to query the API")
    parser.add_argument("--end-date", required=True,
                        help="Formatted end date (YYYY-MM-DD) required to query the API")
    parser.add_argument("--file-location", required=True,
                        help="Location to deliver the file")
    args = parser.parse_args()

    if args.provider_list:
        print "ID\tName"
        for p in Provider.objects.all().order_by('id'):
            print "%d\t%s" % (p.id, p.location)
        return

    try:
        provider_ids = args.provider_ids.split(",")
        generate_report(args.username, args.start_date, args.end_date, provider_ids, args.file_location)
        print "Report completed: %s" % (args.file_location,)
    except Exception as exc:
        print "Failed to generate report: %s" % exc


if __name__ == "__main__":
    main()
