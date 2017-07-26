import collections
import copy
import datetime
import json
from decimal import Decimal

import django
import django.test
import mock
from behave import *

import api.tests.factories
import jetstream
import jetstream.allocation as jetstream_allocation
from jetstream.tests.tas_api_mock_utils import _make_mock_tacc_api_post, _make_mock_tacc_api_get, \
    reset_mock_tas_fixtures


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


@step(u'we clear the local cache')
def we_clear_the_local_cache(context):
    context.driver.clear_cache()
    context.test.assertDictEqual(context.driver.username_map, {})
    context.test.assertListEqual(context.driver.user_project_list, [])
    context.test.assertListEqual(context.driver.project_list, [])
    context.test.assertListEqual(context.driver.allocation_list, [])

    jetstream_allocation.TASAPIDriver.username_map = {}
    jetstream_allocation.TASAPIDriver.user_project_list = []
    jetstream_allocation.TASAPIDriver.project_list = []
    jetstream_allocation.TASAPIDriver.allocation_list = []
    context.test.assertDictEqual(jetstream_allocation.TASAPIDriver.username_map, {})
    context.test.assertListEqual(jetstream_allocation.TASAPIDriver.user_project_list, [])
    context.test.assertListEqual(jetstream_allocation.TASAPIDriver.project_list, [])
    context.test.assertListEqual(jetstream_allocation.TASAPIDriver.allocation_list, [])

    reset_mock_tas_fixtures(context)


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


@given(u'a current time of "{frozen_current_time}"')
@given(u'a current time of \'{frozen_current_time}\'')
@given(u'a current time of "{frozen_current_time}" with tick = {tick}')
@given(u'a current time of \'{frozen_current_time}\' with tick = {tick}')
def current_time(context, frozen_current_time, tick=True):
    context.frozen_current_time = frozen_current_time
    context.freeze_time_with_tick = (tick is True)


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
        payload = expected_event['payload']
        payload_dict = json.loads(payload)
        if hasattr(context, 'persona') and isinstance(context.persona, collections.Mapping):
            # Use Python string formatting to insert persona variables into any template strings
            for key, value in payload_dict.iteritems():
                if isinstance(value, basestring):
                    payload_dict[key] = value.format(**context.persona)
        expected_event['payload'] = payload_dict
    from core.models import EventTable
    query = EventTable.objects.all().order_by('id')
    if event_name is not None:
        query = query.filter(name=event_name)
    fields_we_care_about = context.table.headings
    events = [event for event in query.values(*fields_we_care_about)]
    actual_events_rows = []

    def dump_field(a_field):
        if isinstance(a_field, dict):
            return json.dumps(a_field)
        return a_field

    for event in events:
        event['timestamp'] = event['timestamp'].replace(microsecond=0)
        event['timestamp'] = datetime.datetime.strftime(event['timestamp'], '%Y-%m-%d %H:%M:%S%z')
        actual_event_content = [dump_field(event[field]) for field in fields_we_care_about]
        actual_event_row = '| {} |'.format(' | '.join(actual_event_content))
        actual_events_rows.append(actual_event_row)
    print('actual_events_rows:')
    print('(In case of unexpected events this will provide an easy way to copy valid table values from the console)')
    print('\n'.join(actual_events_rows))
    context.test.maxDiff = None
    context.test.assertListEqual(expected_events, events)


@step("we set up the TAS API failover scenario example")
def setup_tas_api_failover_scenario(context):
    example = dict(zip(context.scenario._row.headings, context.scenario._row.cells))

    if example['has_tas_account'] == 'Yes':
        context.execute_steps(u'''
            Given the following XSEDE to TACC username mappings
              | xsede_username  | tacc_username  |
              | {user}          | tacc_{user}    |
        '''.format(**example))
    else:
        context.execute_steps(u'''
            Given the following XSEDE to TACC username mappings
              | xsede_username  | tacc_username  |
        ''')

    if example['has_valid_allocation'] == 'Yes':
        context.execute_steps(u'''
            Given the following TAS projects
              | id      | chargeCode |
              | {index} | TG_{user}  |
            And the following TAS allocations
              | id      | projectId | project   | computeAllocated | computeUsed | start                | end                  | status | resource  |
              | {index} | {index}   | TG_{user} | 1000000          | 781768.01   | 2016-01-01T06:00:00Z | 2017-06-30T05:00:00Z | Active | Jetstream |
            And the following TACC usernames for TAS projects
              | project   | tacc_usernames |
              | TG_{user} | tacc_{user}    |
        '''.format(**example))
    else:
        context.execute_steps(u'''
            Given the following TAS projects
              | id      | chargeCode |
            And the following TAS allocations
              | id      | projectId | project   | computeAllocated | computeUsed | start                | end                  | status | resource  |
            And the following TACC usernames for TAS projects
              | project   | tacc_usernames |
        '''.format(**example))


@step("the user should be valid - {user_is_valid}")
def step_impl(context, user_is_valid):
    """
    :type context: behave.runner.Context
    :type user_is_valid: str
    """
    import core.models
    context.test.assertIn(user_is_valid, ['Yes', 'No'])
    assert context.persona
    context.test.assertIn('user', context.persona)
    user = context.persona['user']
    context.test.assertIsInstance(user, core.models.AtmosphereUser)
    example = dict(zip(context.scenario._row.headings, context.scenario._row.cells))
    is_tas_up = example.get('is_tas_up', 'Yes') == 'Yes'
    overridden_validation_plugins = ['jetstream.plugins.auth.validation.XsedeProjectRequired']

    with mock.patch.multiple('jetstream.allocation',
                             tacc_api_post=mock.DEFAULT,
                             tacc_api_get=mock.DEFAULT,
                             ) as mock_methods:
        mock_methods['tacc_api_post'].side_effect = jetstream.tests.tas_api_mock_utils._make_mock_tacc_api_post(
            context, is_tas_up)
        mock_methods['tacc_api_get'].side_effect = jetstream.tests.tas_api_mock_utils._make_mock_tacc_api_get(
            context, is_tas_up)
        with django.test.override_settings(
                VALIDATION_PLUGINS=overridden_validation_plugins
        ):
            import core.plugins
            core.plugins.ValidationPluginManager.list_of_classes = getattr(django.conf.settings, 'VALIDATION_PLUGINS',
                                                                           [])
            context.test.assertListEqual(core.plugins.ValidationPluginManager.list_of_classes,
                                         overridden_validation_plugins)
            try:
                if user_is_valid == 'Yes':
                    context.test.assertTrue(user.is_valid())
                elif user_is_valid == 'No':
                    context.test.assertFalse(user.is_valid())
            except Exception as e:
                print('Ruh-roh. {}'.format(e))
                raise
    print('Done')


@step("we ensure local allocation is created or deleted")
def step_impl(context):
    """
    :type context: behave.runner.Context
    :type has_local_allocation: str
    """
    assert context.persona
    context.test.assertIn('user', context.persona)
    user = context.persona['user']
    import core.models
    context.test.assertIsInstance(user, core.models.AtmosphereUser)
    active_allocation_count = core.models.UserAllocationSource.objects.filter(user=user).count()
    example = dict(zip(context.scenario._row.headings, context.scenario._row.cells))
    has_local_allocation = example.get('has_local_allocation', 'Yes')
    if has_local_allocation == 'No':
        core.models.UserAllocationSource.objects.filter(user=user).delete()
        return

    if active_allocation_count > 0:
        return

    allocation_source = api.tests.factories.AllocationSourceFactory.create(name='TG-ALT_{}'.format(user.username),
                                                                           compute_allowed=3000)
    context.test.assertIsInstance(allocation_source, core.models.AllocationSource)

    user_allocation_source = api.tests.factories.UserAllocationSourceFactory.create(user=user,
                                                                                    allocation_source=allocation_source)
    context.test.assertIsInstance(user_allocation_source, core.models.UserAllocationSource)
