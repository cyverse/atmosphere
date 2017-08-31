import collections
import datetime
import decimal
import json
import time
import unittest
import uuid
from unittest import TestCase
from unittest.util import safe_repr

import dateutil.parser
import django.test
import django.urls
import django.utils.timezone
import mock
import rest_framework.test
from behave import *

import api.tests.factories
import jetstream.tests.tas_api_mock_utils


@step('we create a new user')
def create_new_user(context):
    """
    :type context: behave.runner.Context
    """
    assert context.persona
    user = api.tests.factories.UserFactory.create(username=context.persona['username'], is_staff=False,
                                                  is_superuser=False)
    user.set_password(context.persona['password'])
    user.save()
    context.persona['user'] = user


@step('we create a new admin user')
def create_new_admin_user(context):
    """
    :type context: behave.runner.Context
    """
    assert context.persona
    user = api.tests.factories.UserFactory.create(username=context.persona['username'], is_staff=True,
                                                  is_superuser=True)
    user.set_password(context.persona['password'])
    user.save()
    context.persona['user'] = user


@step('I log in')
def i_log_in(context):
    """
    :type context: behave.runner.Context
    """
    assert context.persona
    client = rest_framework.test.APIClient()
    context.persona['client'] = client
    with django.test.modify_settings(AUTHENTICATION_BACKENDS={
        'prepend': 'django.contrib.auth.backends.ModelBackend',
        'remove': ['django_cyverse_auth.authBackends.MockLoginBackend']
    }):
        login_result = client.login(username=context.persona['username'], password=context.persona['password'])
        context.test.assertTrue(login_result)


@step('I log in with valid XSEDE project required and default quota plugin enabled')
def i_log_in(context):
    """
    :type context: behave.runner.Context
    """
    assert context.persona
    client = rest_framework.test.APIClient()
    context.persona['client'] = client
    with django.test.override_settings(
            AUTHENTICATION_BACKENDS=['django_cyverse_auth.authBackends.MockLoginBackend'],
            ALWAYS_AUTH_USER=context.persona['username'],
            DEFAULT_QUOTA_PLUGINS=['jetstream.plugins.quota.default_quota.JetstreamSpecialAllocationQuota'],
    ):
        with django.test.modify_settings(
                VALIDATION_PLUGINS={
                    'prepend': 'jetstream.plugins.auth.validation.XsedeProjectRequired',
                    'remove': 'atmosphere.plugins.auth.validation.AlwaysAllow'
                }
        ):
            login_result = client.login(username=context.persona['username'], password=context.persona['password'])
            context.persona['login_result'] = login_result
            context.test.assertTrue(login_result)
            if 'user' not in context.persona:
                import core.models
                context.persona['user'] = core.models.AtmosphereUser.objects.get_by_natural_key(
                    context.persona['username'])
                assert context.persona['user'].username == context.persona['username']


@step('I try to log in with valid XSEDE project required')
def i_log_in_with_valid_xsede_project_required(context):
    """
    :type context: behave.runner.Context
    """
    assert context.persona
    client = rest_framework.test.APIClient()
    context.persona['client'] = client
    is_tas_up = True
    if hasattr(context.scenario, '_row') and context.scenario._row:
        example = dict(zip(context.scenario._row.headings, context.scenario._row.cells))
        is_tas_up = example.get('is_tas_up', 'Yes') == 'Yes'
    with django.test.override_settings(
            AUTHENTICATION_BACKENDS=['django_cyverse_auth.authBackends.MockLoginBackend'],
            ALWAYS_AUTH_USER=context.persona['username'],
            DEFAULT_QUOTA_PLUGINS=['jetstream.plugins.quota.default_quota.JetstreamSpecialAllocationQuota'],
            VALIDATION_PLUGINS=['jetstream.plugins.auth.validation.XsedeProjectRequired']
    ):
        with mock.patch.multiple('jetstream.allocation',
                                 tacc_api_post=mock.DEFAULT,
                                 tacc_api_get=mock.DEFAULT,
                                 ) as mock_methods:
            mock_methods['tacc_api_post'].side_effect = jetstream.tests.tas_api_mock_utils._make_mock_tacc_api_post(
                context, is_tas_up)
            mock_methods['tacc_api_get'].side_effect = jetstream.tests.tas_api_mock_utils._make_mock_tacc_api_get(
                context, is_tas_up)
            login_result = client.login(username=context.persona['username'], password=context.persona['password'])
            context.persona['login_result'] = login_result


@step('the login attempt should fail')
def login_should_fail(context):
    context.test.assertFalse(context.persona['login_result'])
    context.persona.pop('user', None)


@step('the login attempt should succeed')
def login_should_succeed(context):
    context.test.assertTrue(context.persona['login_result'])
    import core.models
    context.persona['user'] = core.models.AtmosphereUser.objects.get_by_natural_key(
        context.persona['username'])
    assert context.persona['user'].username == context.persona['username']


@step('I get my allocation sources from the API I should see')
def get_allocation_sources_from_api(context):
    assert context.persona
    client = context.persona['client']
    response = client.get('/api/v2/allocation_sources')
    context.persona['response'] = response
    context.test.assertEqual(response.status_code, 200)
    api_allocation_sources = []
    for raw_result in response.data['results']:
        api_result = {}
        for heading in context.table.headings:
            raw_value = raw_result[heading]
            cleaned_value = raw_value
            if isinstance(raw_value, datetime.datetime):
                rounded_datetime = raw_value.replace(microsecond=0)
                formatted_datetime = datetime.datetime.strftime(rounded_datetime, u'%Y-%m-%d %H:%M:%S%z')
                cleaned_value = formatted_datetime
            if heading == 'start_date':
                # a datetime formatted as a string
                parsed_datetime = dateutil.parser.parse(raw_value)
                rounded_datetime = parsed_datetime.replace(microsecond=0)
                formatted_datetime = datetime.datetime.strftime(rounded_datetime, u'%Y-%m-%d %H:%M:%S%z')
                cleaned_value = formatted_datetime
            api_result[heading] = cleaned_value
        api_allocation_sources.append(api_result)

    raw_expected_allocation_sources = [dict(zip(row.headings, row.cells)) for row in context.table]
    expected_allocation_sources = []
    transform_map = {
        'name': unicode,
        'compute_allowed': int,
        'start_date': str,
        'end_date': lambda x: None if x == 'None' else unicode(x),
        'compute_used': decimal.Decimal,
        'global_burn_rate': decimal.Decimal,
        'updated': str,
        'renewal_strategy': unicode,
        'user_compute_used': decimal.Decimal,
        'user_burn_rate': decimal.Decimal,
        'user_snapshot_updated': str
    }
    for raw_row in raw_expected_allocation_sources:
        clean_row = {}
        for key, value in raw_row.iteritems():
            transform = transform_map[key]
            clean_row[key] = transform(value)
        expected_allocation_sources.append(clean_row)

    context.test.maxDiff = None
    context.test.assertItemsEqual(expected_allocation_sources, api_allocation_sources)
    # For debugging, use `assertListEqual` below if `assertItemsEqual` above is not clear
    # context.test.assertListEqual(expected_allocation_sources, api_allocation_sources)


@step('we create an allocation source through the API')
def we_create_allocation_source_through_api(context):
    assert context.persona
    client = context.persona['client']
    for row in context.table:
        response = client.post('/api/v2/allocation_sources',
                               {
                                   'renewal_strategy': row['renewal strategy'],
                                   'name': row['name'],
                                   'compute_allowed': row['compute allowed']
                               })
        if 'uuid' in response.data and response.data['uuid']:
            allocation_source_ids = context.persona.get('allocation_source_ids', {})
            allocation_source_ids[row['name']] = response.data['uuid']
            context.persona['allocation_source_ids'] = allocation_source_ids


@step('we assign allocation source "{allocation_source_name}" to user "{username}" via the API')
def assign_allocation_source_to_user_via_api(context, allocation_source_name, username):
    assert context.persona
    client = context.persona['client']
    allocation_source_id = context.persona['allocation_source_ids'][allocation_source_name]
    context.persona['response'] = client.post('/api/v2/user_allocation_sources',
                                              {
                                                  'username': username,
                                                  'source_id': allocation_source_id
                                              })


@step('we create a provider "{provider_location}"')
def set_up_provider(context, provider_location):
    assert context.persona
    import core.models
    provider = api.tests.factories.ProviderFactory.create(location=provider_location, public=True, type__name='mock')
    core.models.ProviderCredential.objects.get_or_create(
        provider=provider,
        key='auth_url',
        value='https://localhost/')
    core.models.ProviderCredential.objects.get_or_create(
        provider=provider,
        key='project_name',
        value='some_project')
    core.models.ProviderCredential.objects.get_or_create(
        provider=provider,
        key='region_name',
        value='some_region')
    core.models.ProviderCredential.objects.get_or_create(
        provider=provider,
        key='admin_url',
        value='https://localhost/')

    context.persona['provider'] = provider


@step('we create an account for the current persona on provider "{provider_location}"')
def create_jetstream_account(context, provider_location):
    """This does not use the factory
    
    We want to test the default quota plugin.

    NOTE: At the moment this step only works with Jetstream and TAS API
    """
    assert context.persona
    import core.models
    context.test.assertIn('jetstream', django.conf.settings.INSTALLED_APPS,
                          'Step only works with Jetstream setup. '
                          'Please use "we create an identity for the current persona ..."')
    provider = core.models.Provider.objects.get(location=provider_location)
    user = context.persona['user']
    with mock.patch('service.driver.get_account_driver', autospec=True) as mock_get_account_driver:
        mock_account_driver = mock.MagicMock(provider)

        def mock_create_account_method(username, password=None, project_name=None,
                                       role_name=None, quota=None, max_quota=False):
            factory_identity = api.tests.factories.IdentityFactory.create_identity(
                created_by=user,
                provider=provider,
                quota=quota)
            return factory_identity

        mock_account_driver.create_account = mock.MagicMock(side_effect=mock_create_account_method)
        mock_get_account_driver.return_value = mock_account_driver
        with mock.patch.multiple('jetstream.allocation',
                                 tacc_api_post=mock.DEFAULT,
                                 tacc_api_get=mock.DEFAULT,
                                 ) as mock_methods:
            mock_methods['tacc_api_post'].side_effect = jetstream.tests.tas_api_mock_utils._make_mock_tacc_api_post(
                context)
            mock_methods['tacc_api_get'].side_effect = jetstream.tests.tas_api_mock_utils._make_mock_tacc_api_get(
                context)
            with django.test.override_settings(
                    DEFAULT_QUOTA_PLUGINS=['jetstream.plugins.quota.default_quota.JetstreamSpecialAllocationQuota']
            ):
                import core.plugins
                core.plugins.DefaultQuotaPluginManager.list_of_classes = getattr(django.conf.settings,
                                                                                 'DEFAULT_QUOTA_PLUGINS', [])
                new_identity = core.models.user.create_new_account_for(provider, user)

    context.persona['user_identity'] = new_identity


@step('we create an identity for the current persona on provider "{provider_location}"')
def create_identity(context, provider_location):
    assert context.persona
    import core.models
    provider = core.models.Provider.objects.get(location=provider_location)
    user_identity = api.tests.factories.IdentityFactory.create_identity(
        created_by=context.persona['user'],
        provider=provider)
    context.persona['user_identity'] = user_identity


@step('I should have the following quota on provider "{}"')
def should_have_quota_on_provider(context, provider_location):
    assert context.persona
    import core.models
    provider = core.models.Provider.objects.get(location=provider_location)
    username = context.persona['username']
    user_identity = core.models.user.get_default_identity(username, provider)
    expected_quota = dict([(row[0], int(row[1])) for row in context.table.rows])
    quota_keys = expected_quota.keys()
    actual_quota = user_identity.quota
    actual_quota_dict = dict([(key, getattr(actual_quota, key)) for key in quota_keys])
    context.test.assertDictEqual(expected_quota, actual_quota_dict)


@step('we make the current identity the admin on provider "{provider_location}"')
def create_identity(context, provider_location):
    assert context.persona
    import core.models
    provider = core.models.Provider.objects.get(location=provider_location)
    user_identity = context.persona['user_identity']
    core.models.AccountProvider.objects.get_or_create(
        provider=provider,
        identity=user_identity)
    core.models.Identity.update_credential(user_identity, 'key', 'admin', replace=True)
    core.models.Identity.update_credential(user_identity, 'secret', 'adminsecret', replace=True)
    core.models.Identity.update_credential(user_identity, 'secret', 'adminsecret', replace=True)


@step('we create a provider machine for current persona')
def create_provider_machine(context):
    assert context.persona
    user_identity = context.persona['user_identity']
    user = context.persona['user']
    provider_machine = api.tests.factories.ProviderMachineFactory.create_provider_machine(user, user_identity)
    context.persona['provider_machine'] = provider_machine


@step('I get the projects via the API')
def get_projects_api(context):
    assert context.persona
    client = context.persona['client']
    url = '/api/v2/projects'
    response = client.get(url)
    context.persona['response'] = response


@step('I create a project called "{project_name}" via the API')
def create_project_api(context, project_name):
    assert context.persona
    client = context.persona['client']
    user = context.persona['user']
    from core.models import AtmosphereUser, Identity
    assert isinstance(user, AtmosphereUser)
    owner_group_name = user.username
    url = '/api/v2/projects'
    response = client.post(url,
                           {
                               'name': project_name,
                               'description': project_name,
                               'owner': owner_group_name
                           })
    context.persona['response'] = response


@when('I create a volume with name "{volume_name}" and size {volume_size:d} using API')
def create_volume_api(context, volume_name, volume_size):
    assert context.persona
    client = context.persona['client']
    user_identity = context.persona['user_identity']
    import core.models
    context.test.assertIsInstance(user_identity, core.models.Identity)
    context.test.assertIsInstance(user_identity.provider, core.models.Provider)
    url = '/api/v1/provider/{}/identity/{}/volume'.format(user_identity.provider.uuid, user_identity.uuid)
    post_data = {
        'name': volume_name,
        'size': volume_size
    }
    with mock.patch('service.volume.check_over_storage_quota', autospec=True) as mock_check_over_storage_quota:
        mock_check_over_storage_quota.return_value = True
        response = client.post(url, post_data, format='json')
    context.persona['response'] = response


@step('I get the volumes via the API')
def get_volumes_api(context):
    assert context.persona
    client = context.persona['client']
    user_identity = context.persona['user_identity']
    import core.models
    context.test.assertIsInstance(user_identity, core.models.Identity)
    context.test.assertIsInstance(user_identity.provider, core.models.Provider)
    url = '/api/v1/provider/{}/identity/{}/volume'.format(user_identity.provider.uuid, user_identity.uuid)
    with mock.patch('service.volume.check_over_storage_quota', autospec=True) as mock_check_over_storage_quota:
        mock_check_over_storage_quota.return_value = True
        response = client.get(url)
    context.persona['response'] = response


@step('we get the project volumes via the API')
def get_project_volumes_api(context):
    assert context.persona
    client = context.persona['client']
    user_identity = context.persona['user_identity']
    project_volume_id = context.persona['project_volume_id']
    import core.models
    context.test.assertIsInstance(user_identity, core.models.Identity)
    context.test.assertIsInstance(user_identity.provider, core.models.Provider)
    url = '/api/v2/project_volumes/{}'.format(project_volume_id)
    response = client.get(url)
    context.persona['response'] = response


@when('I associate volume "{volume_id_var}" with project "{project_id_var}" via the API')
def associate_volume_with_project(context, volume_id_var, project_id_var):
    assert context.persona
    client = context.persona['client']
    user_identity = context.persona['user_identity']
    import core.models
    context.test.assertIsInstance(user_identity, core.models.Identity)
    context.test.assertIsInstance(user_identity.provider, core.models.Provider)
    url = '/api/v2/project_volumes'
    volume_id = context.persona[volume_id_var]
    project_id = context.persona[project_id_var]
    post_data = {
        'project': project_id,
        'volume': volume_id
    }
    response = client.post(url, post_data, format='json')
    context.persona['response'] = response

@step('we create an active instance')
def create_active_instance(context):
    assert context.persona
    user = context.persona['user']
    user_identity = context.persona['user_identity']
    provider_machine = context.persona['provider_machine']
    import core.models
    context.test.assertIsInstance(provider_machine, core.models.ProviderMachine)
    provider = provider_machine.provider

    active_instance = api.tests.factories.InstanceFactory.create(name='Instance in active', provider_alias=uuid.uuid4(),
                                                                 source=provider_machine.instance_source,
                                                                 created_by=user,
                                                                 created_by_identity=user_identity,
                                                                 start_date=django.utils.timezone.now())

    active_status = api.tests.factories.InstanceStatusFactory.create(name='active')
    single_cpu_size = api.tests.factories.SizeFactory.create(
        name='single_cpu_size',
        provider=provider,
        cpu=1,
        disk=100,
        root=10,
        mem=4096
    )
    api.tests.factories.InstanceHistoryFactory.create(
        status=active_status,
        activity='',
        instance=active_instance,
        size=single_cpu_size
    )

    context.persona['active_instance'] = active_instance


@step('I set "{key}" to attribute "{attribute}" of "{persona_var}"')
@step('I set "{key}" to another variable "{persona_var}"')
def set_key_to_persona_var_and_attribute(context, key, persona_var, attribute=None):
    assert context.persona is not None, u'no persona is setup'
    if attribute:
        context.persona[key] = getattr(context.persona[persona_var], attribute)
    else:
        context.persona[key] = context.persona[persona_var]


@step(u'I set "{key}" to key "{other_key}" of "{persona_var}"')
def set_key_to_key_of_persona_var(context, key, persona_var, other_key):
    assert context.persona
    context.test.assertIn(persona_var, context.persona)
    context.test.assertIsInstance(context.persona[persona_var], dict)
    context.test.assertIn(other_key, context.persona[persona_var])
    context.persona[key] = context.persona[persona_var][other_key]


@step('I set "{key}" to allocation source with name "{allocation_source_name}"')
def set_key_to_persona_var_and_attribute(context, key, allocation_source_name):
    assert context.persona is not None, u'no persona is setup'
    import core.models
    allocation_source = core.models.AllocationSource.objects.get(name=allocation_source_name)
    context.persona[key] = allocation_source


@when('we get the details for the active instance via the API')
def get_details_for_active_instance(context):
    assert context.persona
    client = context.persona['client']
    active_instance = context.persona['active_instance']
    url = django.urls.reverse('api:v2:instance-detail',
                              args=(active_instance.provider_alias,))

    # Try a few times. Sometimes this does not find the instance on the first try.
    for i in range(10):
        response = client.get(url)
        if 'version' in response.data:
            continue
        time.sleep(0.1)
    context.persona['response'] = response
    context.persona['provider_alias'] = response.data['version']['id']


@when('I assign allocation source "{allocation_source_name}" to active instance')
def assign_allocation_source_to_active_instance(context, allocation_source_name):
    assert context.persona
    active_instance = context.persona['active_instance']
    client = context.persona['client']
    response = client.post('/api/v2/instance_allocation_source',
                           {
                               'instance_id': active_instance.provider_alias,
                               'allocation_source_name': allocation_source_name
                           })
    context.persona['response'] = response


@when('I change the name of the active instance to "{new_instance_name}"')
def change_name_of_active_instance(context, new_instance_name):
    assert context.persona
    active_instance = context.persona['active_instance']
    client = context.persona['client']
    response = client.patch('/api/v2/instances/{}'.format(active_instance.id),
                           {
                               'name': new_instance_name
                           })
    context.persona['response'] = response


@step('the API response code is {response_code:d}')
def api_response_code_is(context, response_code):
    assert context.persona
    assert isinstance(context.test, unittest.case.TestCase)
    context.test.assertEqual(context.persona['response'].status_code, response_code)


@step("the API response contains")
def api_response_contains(context):
    assert context.persona
    context.test.assertIn('response', context.persona)
    response = context.persona['response']

    formatted_text = context.text % dict(context.persona)
    expected_response = json.loads(formatted_text)

    if isinstance(expected_response, collections.Sequence) and hasattr(expected_response, '__iter__'):
        context.test.assertSequenceRecursive(expected_response, response.data)
    else:
        context.test.assertDictContainsSubsetRecursive(expected_response, response.data)


def assertSequenceRecursive(self, expected, actual, depth=0, msg=None):
    assert isinstance(self, TestCase)
    missing = []
    mismatched = []
    self.assertIsInstance(expected, collections.Sequence)
    self.assertIsInstance(actual, collections.Sequence)
    self.assertEqual(len(expected), len(actual), msg='Lengths are different: {} vs {}'.format(expected, actual))
    for expected_item, actual_item in zip(expected, actual):
        if isinstance(actual_item, datetime.datetime):
            actual_item = datetime.datetime.strftime(actual_item, '%Y-%m-%d %H:%M:%S%z')
        if isinstance(expected_item, datetime.datetime):
            expected_item = datetime.datetime.strftime(expected_item, '%Y-%m-%d %H:%M:%S%z')
        if isinstance(actual_item, collections.Mapping):
            missing_1, mismatched_1 = self.assertDictContainsSubsetRecursive(expected_item, actual_item,
                                                                             depth=depth + 1)
            missing.extend(missing_1)
            mismatched.extend(mismatched_1)
        elif isinstance(actual_item, collections.Sequence) and hasattr(actual_item, '__iter__'):
            missing_1, mismatched_1 = self.assertSequenceRecursive(expected_item, actual_item, depth=depth + 1)
            missing.extend(missing_1)
            mismatched.extend(mismatched_1)
        elif expected_item != actual_item:
            mismatched.append('expected: %s, actual: %s' % (safe_repr(expected_item), safe_repr(actual_item)))

    if depth > 0:
        return missing, mismatched

    if not (missing or mismatched):
        return

    standardMsg = ''
    if missing:
        standardMsg = 'Missing: %s' % ','.join(safe_repr(m) for m in
                                               missing)
    if mismatched:
        if standardMsg:
            standardMsg += '; '
        standardMsg += 'Mismatched values: %s' % ','.join(mismatched)

    self.fail(self._formatMessage(msg, standardMsg))


def assertDictContainsSubsetRecursive(self, expected, actual, depth=0, msg=None):
    assert isinstance(self, TestCase)
    self.assertIsInstance(expected, collections.Mapping)
    self.assertIsInstance(actual, collections.Mapping)
    missing = []
    mismatched = []
    for key, value in expected.iteritems():
        if isinstance(value, datetime.datetime):
            value = datetime.datetime.strftime(value, '%Y-%m-%d %H:%M:%S%z')
        if isinstance(actual[key], datetime.datetime):
            actual[key] = datetime.datetime.strftime(actual[key], '%Y-%m-%d %H:%M:%S%z')
        if key not in actual:
            missing.append(key)
        elif isinstance(actual[key], collections.Mapping):
            missing_1, mismatched_1 = self.assertDictContainsSubsetRecursive(value, actual[key], depth=depth + 1)
            missing.extend(missing_1)
            mismatched.extend(mismatched_1)
        elif isinstance(actual[key], collections.Sequence) and hasattr(actual[key], '__iter__'):
            missing_1, mismatched_1 = self.assertSequenceRecursive(value, actual[key], depth=depth + 1)
            missing.extend(missing_1)
            mismatched.extend(mismatched_1)
        elif value != actual[key]:
            mismatched.append('%s, expected: %s, actual: %s' %
                              (safe_repr(key), safe_repr(value),
                               safe_repr(actual[key])))

    if depth > 0:
        return missing, mismatched

    if not (missing or mismatched):
        return

    standardMsg = ''
    if missing:
        standardMsg = 'Missing: %s' % ','.join(safe_repr(m) for m in
                                               missing)
    if mismatched:
        if standardMsg:
            standardMsg += '; '
        standardMsg += 'Mismatched values: %s' % ','.join(mismatched)

    self.fail(self._formatMessage(msg, standardMsg))

TestCase.assertSequenceRecursive = assertSequenceRecursive
TestCase.assertDictContainsSubsetRecursive = assertDictContainsSubsetRecursive


@step(u'"{key}" contains')
def dict_variable_contains(context, key):
    assert context.persona
    context.test.assertIn(key, context.persona)
    value = context.persona[key]
    context.test.assertIsInstance(value, dict)
    expected_value = json.loads(context.text)
    context.test.assertDictContainsSubset(expected_value, value)


@step('a dummy browser')
def dummy_browser(context):
    context.single_browser = True
    context.browser = 'dummy'
    context.is_connected = True


@step('we ensure that the user has an allocation source')
def ensure_user_has_allocation_source(context):
    """
    :type context: behave.runner.Context
    """
    assert context.persona
    context.test.assertIn('user', context.persona)
    user = context.persona['user']
    import core.models
    context.test.assertIsInstance(user, core.models.AtmosphereUser)
    import core.plugins
    has_allocations = core.plugins.AllocationSourcePluginManager.ensure_user_allocation_sources(user)
    context.test.assertTrue(has_allocations)


@when('we update CyVerse snapshots')
def update_cyverse_snapshots(context):
    """
    TODO: Combine with `we update snapshots`, and make it a `AllocationSourcePlugin` function
    :type context: behave.runner.Context
    """
    import cyverse_allocation.tasks
    cyverse_allocation.tasks.update_snapshot_cyverse()