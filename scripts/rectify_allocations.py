import json

import django
from dateutil.parser import parse

django.setup()
import logging
import sys
# from latest_json import data as json_data  # Comment this line on prod server
from pprint import pprint
from django.utils import timezone
from core.models.user import AtmosphereUser
from core.models.allocation_source import (
    AllocationSource,
    total_usage)
from jetstream.models import TASAllocationReport, TASAPIDriver
from jetstream.exceptions import TASPluginException
# cached tacc usernames. Do not use in prod
#from tacc_user_list import tacc_username_list

logger = logging.getLogger(__name__)

USE_TAS_PROD = False

if USE_TAS_PROD:
    from atmosphere.settings.local import TACC_API_URL, TACC_API_USER, TACC_API_PASS
else:
    from atmosphere.settings.local import BETA_TACC_API_URL as TACC_API_URL, BETA_TACC_API_USER as TACC_API_USER, \
        BETA_TACC_API_PASS as TACC_API_PASS


def calculate_correction():
    print 'START calculate_correction'
    end_date = TASAllocationReport.objects.all().order_by('end_date').last().end_date
    users = AtmosphereUser.objects.all()
    driver = TASAPIDriver(TACC_API_URL, TACC_API_USER, TACC_API_PASS)
    output = []
    # uncomment this line in prod
    try:
        print 'Going to try loading usernames from JSON'
        with open('tacc_usernames.json', 'r') as f:
            tacc_username_list = json.load(f)
        print tacc_username_list
        print 'Loaded usernames'
    except:
        print 'Failed at loading usernames from JSON. About to get usernames from TAS API'
        tacc_username_list = {user.username: driver.get_tacc_username(user) for
                              user in users}
        print tacc_username_list
        print 'Got usernames'
        with open('tacc_usernames.json', 'w') as f:
            json.dump(tacc_username_list, f)
    print 'About to start calculating corrections'
    for allocation_source in AllocationSource.objects.all():
        output.extend(
            calculate_correction_for(
                allocation_source,
                end_date,
                tacc_username_list))
    print 'END calculate_correction'
    return output


def calculate_correction_for(allocation_source, end_date, tacc_username_list):
    print 'START calculate_correction_for: %s' % allocation_source.name
    correction_delta = []

    for user in allocation_source.all_users:
        username = user.username
        compute_used_atmo = total_usage(
            username,
            start_date=user.date_joined,
            allocation_source_name=allocation_source.name,
            end_date=end_date)
    # TODO : Create snapshots of TAS reports for consistency
        compute_used_jetstream, usage_not_reported = calculate_total_allocation_for_user(
            tacc_username_list[username], allocation_source)
        delta = round(float(compute_used_atmo) -
                      float(compute_used_jetstream), 3)

        correction_delta.append((
            user,
            tacc_username_list[username],
            allocation_source.name,
            allocation_source.source_id,
            delta,
            usage_not_reported))
    print 'END calculate_correction_for: %s' % allocation_source.name
    return correction_delta


def calculate_total_allocation_for_user(username, allocation_source):
    total_used = 0
    usage_not_reported = 0
    reports = TASAllocationReport.objects.filter(resource_name="Jetstream").filter(
        username=username).filter(project_name=allocation_source.name)
    for report in reports:
        if not report.success:
            usage_not_reported += report.compute_used
        total_used += report.compute_used
    return total_used, float(usage_not_reported)


def create_reports(correction_data):
    """
    GO through the list of all users or all providers
    For each username, get an XSede API map to the 'TACC username'
    if 'TACC username' includes a jetstream resource, create a report
    """
    print 'START create_reports'
    end_date = TASAllocationReport.objects.all().order_by('-end_date').first().end_date
    # user_allocation_list = UserAllocationSource.objects.all()
    # all_reports = []
    # driver = TASAPIDriver()
    # for item in user_allocation_list:
    user = correction_data[0]
    allocation_id = correction_data[3]
    tacc_username = correction_data[1]
    project_name = correction_data[2]
    correction_value = correction_data[4]
    project_report = _create_tas_report_for(
        user,
        tacc_username,
        project_name,
        end_date,
        correction_value)
    print 'END create_reports'
    return project_report


def _create_tas_report_for(user, tacc_username, tacc_project_name, end_date, correction_value):
    """
    Create a new report
    """
    if not user:
        raise TASPluginException("User missing")
    if not tacc_username:
        raise TASPluginException("TACC Username missing")
    if not tacc_project_name:
        raise TASPluginException("OpenStack/TACC Project missing")

    last_report = TASAllocationReport.objects.filter(
        project_name=tacc_project_name,
        username=user
    ).order_by('end_date').last()
    if not last_report:
        start_date = user.date_joined
    else:
        start_date = last_report.end_date
    new_report = TASAllocationReport.objects.create(
        user=user,
        username=tacc_username,
        project_name=tacc_project_name,
        compute_used=correction_value,
        start_date=start_date,
        end_date=end_date,
        tacc_api=TACC_API_URL)
    logger.info("Created New Report:%s" % new_report)
    return new_report

if __name__ == '__main__':
    # use this in production
    # tas_obj = TASAPIDriver()
    # json_data = tas_obj.get_all_allocations()

    if len(sys.argv) > 1 and sys.argv[1] == '--create':
        delta = calculate_correction()
        for row in delta:
            correction_value = row[4]
            if correction_value:
                create_reports(row)
    else:
        pprint(calculate_correction())
