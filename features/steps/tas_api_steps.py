import copy
import datetime
import json
from decimal import Decimal

import mock
from behave import *

import api.tests.factories
import jetstream.allocation as jetstream_allocation
from jetstream.tests.tas_api_mock_utils import _make_mock_tacc_api_post, _make_mock_tacc_api_get


@given(u'the following Atmosphere users')
def these_atmosphere_users(context):
    atmo_users = [dict(zip(row.headings, row.cells)) for row in context.table]
    for atmo_user in atmo_users:
        user = api.tests.factories.UserFactory.create(username=atmo_user['username'])
        user.set_password(atmo_user['username'])
        user.save()


@given(u'a TAS API driver')
def a_tas_api_driver(context):
    context.driver = jetstream_allocation.TASAPIDriver()


@given(u'we clear the local cache')
def we_clear_the_local_cache(context):
    context.driver.clear_cache()
    context.test.assertDictEqual(context.driver.username_map, {})
    context.test.assertListEqual(context.driver.user_project_list, [])
    context.test.assertListEqual(context.driver.project_list, [])
    context.test.assertListEqual(context.driver.allocation_list, [])


@given(u'the following XSEDE to TACC username mappings')
def xsede_to_tacc_username_mappings(context):
    context.xsede_to_tacc_username_mapping = dict(row.cells for row in context.table)


@given(u'the following TAS projects')
def these_tas_projects(context):
    context.tas_projects = [dict(zip(row.headings, row.cells)) for row in context.table]
    for tas_project in context.tas_projects:
        tas_project['allocations'] = []


@given(u'the following TAS allocations')
def these_tas_allocations(context):
    context.tas_allocations = [dict(zip(row.headings, row.cells)) for row in context.table]
    for tas_allocation in context.tas_allocations:
        matching_tas_project = \
            [project for project in context.tas_projects if project['id'] == tas_allocation['projectId']][0]
        matching_tas_project['allocations'].append(tas_allocation)


@given(u'the following TACC usernames for TAS projects')
def these_tacc_usernames_for_tas_projects(context):
    context.tas_project_to_tacc_username_mapping = dict(
        (row.cells[0], row.cells[1].split(','),) for row in context.table)

    context.tacc_username_to_tas_project_mapping = {}
    for tas_project, tacc_usernames in context.tas_project_to_tacc_username_mapping.iteritems():
        for tacc_username in tacc_usernames:
            user_tas_projects = context.tacc_username_to_tas_project_mapping.get(tacc_username, set())
            user_tas_projects.add(tas_project)
            context.tacc_username_to_tas_project_mapping[tacc_username] = user_tas_projects


@when(u'we get all projects')
def we_get_all_projects(context):
    with mock.patch.multiple('jetstream.allocation',
                             tacc_api_post=mock.DEFAULT,
                             tacc_api_get=mock.DEFAULT,
                             ) as mock_methods:
        mock_methods['tacc_api_post'].side_effect = _make_mock_tacc_api_post(context)
        mock_methods['tacc_api_get'].side_effect = _make_mock_tacc_api_get(context)
        all_projects = context.driver.get_all_projects()
    context.test.assertListEqual(all_projects, context.tas_projects)
    context.test.assertListEqual(context.driver.project_list, context.tas_projects)
    # Have to this below otherwise it loses the project_list between steps.
    context.driver.project_list = all_projects


@when(u'we fill user allocation sources from TAS')
def we_fill_user_allocation_sources_from_tas(context):
    with mock.patch.multiple('jetstream.allocation',
                             tacc_api_post=mock.DEFAULT,
                             tacc_api_get=mock.DEFAULT,
                             ) as mock_methods:
        mock_methods['tacc_api_post'].side_effect = _make_mock_tacc_api_post(context)
        mock_methods['tacc_api_get'].side_effect = _make_mock_tacc_api_get(context)
        jetstream_allocation.fill_user_allocation_sources()
    pass


@then(u'we should have the following local username mappings')
def we_should_have_the_following_local_username_mappings(context):
    expected_username_map = dict(row.cells for row in context.table)
    context.test.assertDictEqual(expected_username_map, jetstream_allocation.TASAPIDriver.username_map)


@then(u'we should have the following local projects')
def we_should_have_the_following_local_projects(context):
    expected_local_projects = [dict(zip(row.headings, row.cells)) for row in context.table]
    projects_without_allocations = []
    for project in context.driver.project_list:
        project_without_allocations = copy.copy(project)
        del project_without_allocations['allocations']
        projects_without_allocations.append(project_without_allocations)
    context.test.assertListEqual(expected_local_projects, projects_without_allocations)


@then(u'we should have the following local allocations')
def we_should_have_the_following_local_allocations(context):
    expected_local_allocations = [dict(zip(row.headings, row.cells)) for row in context.table]
    context.test.maxDiff = None
    local_allocations = []
    for local_project in context.driver.project_list:
        for local_allocation in local_project['allocations']:
            local_allocations.append(local_allocation)
    context.test.assertListEqual(expected_local_allocations, local_allocations)


@given(u'a current time of \'{frozen_current_time}\'')
def current_time(context, frozen_current_time):
    context.frozen_current_time = frozen_current_time


@when(u'we update snapshots')
def update_snapshots(context):
    from jetstream.tasks import update_snapshot
    with mock.patch.multiple('jetstream.allocation',
                             tacc_api_post=mock.DEFAULT,
                             tacc_api_get=mock.DEFAULT,
                             ) as mock_methods:
        mock_methods['tacc_api_post'].side_effect = _make_mock_tacc_api_post(context)
        mock_methods['tacc_api_get'].side_effect = _make_mock_tacc_api_get(context)
        update_snapshot()


@then(u'we should have the following allocation sources')
def should_have_allocation_sources(context):
    expected_allocation_sources = dict((row.cells[0], Decimal(row.cells[1]),) for row in context.table)
    from core.models import AllocationSource
    allocation_sources = {item['name']: item['compute_allowed'] for item in
                          AllocationSource.objects.all().order_by('name').values('name', 'compute_allowed')}
    context.test.assertDictEqual(expected_allocation_sources, allocation_sources)


@then(u'we should have the following allocation source snapshots')
def should_have_allocation_source_snapshots(context):
    expected_allocation_source_snapshots = dict((row.cells[0], Decimal(row.cells[1]),) for row in context.table)
    from core.models import AllocationSourceSnapshot
    allocation_source_snapshots = {item['allocation_source__name']: item['compute_used'] for item in
                                   AllocationSourceSnapshot.objects.all().values('allocation_source__name',
                                                                                 'compute_used')}
    context.test.assertDictEqual(expected_allocation_source_snapshots, allocation_source_snapshots)


@step(u'we should have the following user allocation sources')
def should_have_user_allocation_sources(context):
    expected_user_allocation_sources = [(row.cells[0], row.cells[1] or None,) for row in context.table]
    from core.models import UserAllocationSource
    user_allocation_sources = [(item['user__username'], item['allocation_source__name'],) for item in
                               UserAllocationSource.objects.all().order_by(
                                   'user__username',
                                   'allocation_source__name'
                               ).values(
                                   'user__username',
                                   'allocation_source__name'
                               )]
    context.test.assertItemsEqual(expected_user_allocation_sources, user_allocation_sources)


@then(u'we should have the following user allocation source snapshots')
def should_have_user_allocation_source_snapshots(context):
    raw_expected_allocation_source_snapshots = [dict(zip(row.headings, row.cells)) for row in context.table]
    expected_allocation_source_snapshots = [
        {
            'atmosphere_username': raw_snapshot['atmosphere_username'],
            'allocation_source': raw_snapshot['allocation_source'],
            'compute_used': Decimal(raw_snapshot['compute_used']),
            'burn_rate': Decimal(raw_snapshot['burn_rate'])
        }
        for raw_snapshot in raw_expected_allocation_source_snapshots
    ]

    import core.models
    raw_user_allocation_source_snapshots = core.models.UserAllocationSnapshot.objects.all().values(
        'user__username',
        'allocation_source__name',
        'compute_used',
        'burn_rate'
    ).order_by('user__username', 'allocation_source__name')
    user_allocation_source_snapshots = [
        {
            'atmosphere_username': raw_snapshot['user__username'],
            'allocation_source': raw_snapshot['allocation_source__name'],
            'compute_used': raw_snapshot['compute_used'],
            'burn_rate': raw_snapshot['burn_rate']
        }
        for raw_snapshot in raw_user_allocation_source_snapshots
    ]

    context.test.maxDiff = None
    context.test.assertItemsEqual(expected_allocation_source_snapshots, user_allocation_source_snapshots)


@step(u'we should have the following events')
@step(u'we should have the following "{event_name}" events')
def should_have_following_events(context, event_name=None):
    expected_events = [dict(zip(row.headings, row.cells)) for row in context.table]
    for expected_event in expected_events:
        expected_event['payload'] = json.loads(expected_event['payload'])
    from core.models import EventTable
    query = EventTable.objects.all().order_by('id')
    if event_name is not None:
        query = query.filter(name=event_name)
    events = [event for event in query.values('entity_id', 'name', 'payload', 'timestamp')]
    for event in events:
        event['timestamp'] = event['timestamp'].replace(microsecond=0)
        event['timestamp'] = datetime.datetime.strftime(event['timestamp'], '%Y-%m-%d %H:%M:%S%z')
    context.test.maxDiff = None
    context.test.assertListEqual(expected_events, events)
