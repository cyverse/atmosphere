from behave import *
import mock

import jetstream.allocation as jetstream_allocation
import jetstream.exceptions as jetstream_exceptions


def _make_mock_xsede_to_tacc_username(xsede_to_tacc_username_mapping):
    def _mock_xsede_to_tacc_username(xsede_username):
        if xsede_username not in xsede_to_tacc_username_mapping:
            raise jetstream_exceptions.TASAPINoValidUsernameFound(xsede_username)

        return xsede_to_tacc_username_mapping[xsede_username]

    return _mock_xsede_to_tacc_username


def _make_mock_get_all_projects(tas_projects):
    def _mock_get_all_projects():
        return tas_projects

    return _mock_get_all_projects


def _make_mock_project_users(tas_project_to_tacc_username_mapping):
    def _mock_get_project_users(project_id):
        return tas_project_to_tacc_username_mapping[project_id]

    return _mock_get_project_users


@given(u'the following Atmosphere users')
def these_atmosphere_users(context):
    from core.models import AtmosphereUser
    atmo_users = [dict(zip(row.headings, row.cells)) for row in context.table]
    for atmo_user in atmo_users:
        AtmosphereUser.objects.create(username=atmo_user['username'])


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


@when(u'we get all projects')
def we_get_all_projects(context):
    with mock.patch.multiple('jetstream.allocation.TASAPIDriver',
                             _get_all_projects=mock.DEFAULT
                             ) as mock_methods:
        mock_methods['_get_all_projects'].side_effect = _make_mock_get_all_projects(context.tas_projects)
        all_projects = context.driver.get_all_projects()
    new_driver = jetstream_allocation.TASAPIDriver()
    context.test.assertListEqual(new_driver.project_list, context.tas_projects)


@when(u'we fill user allocation sources from TAS')
def we_fill_user_allocation_sources_from_tas(context):
    with mock.patch.multiple('jetstream.allocation.TASAPIDriver',
                             _xsede_to_tacc_username=mock.DEFAULT,
                             _get_all_projects=mock.DEFAULT,
                             get_project_users=mock.DEFAULT
                             ) as mock_methods:
        mock_methods['_xsede_to_tacc_username'].side_effect = _make_mock_xsede_to_tacc_username(
            context.xsede_to_tacc_username_mapping)
        mock_methods['_get_all_projects'].side_effect = _make_mock_get_all_projects(context.tas_projects)
        mock_methods['get_project_users'].side_effect = _make_mock_project_users(
            context.tas_project_to_tacc_username_mapping)
        jetstream_allocation.fill_user_allocation_sources()
    pass


@then(u'we should have the following local username mappings')
def we_should_have_the_following_local_username_mappings(context):
    expected_username_map = dict(row.cells for row in context.table)
    context.test.assertDictEqual(jetstream_allocation.TASAPIDriver.username_map, expected_username_map)


@then(u'we should have the following local projects')
def we_should_have_the_following_local_projects(context):
    expected_local_projects = [dict(zip(row.headings, row.cells)) for row in context.table]
    new_driver = jetstream_allocation.TASAPIDriver()
    context.test.assertListEqual(new_driver.project_list, expected_local_projects)
