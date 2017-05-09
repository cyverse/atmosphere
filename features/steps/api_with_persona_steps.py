import datetime
import decimal
import unittest
import uuid

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
            context.test.assertTrue(login_result)
            if 'user' not in context.persona:
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
def create_account(context, provider_location):
    """This does not use the factory
    
    We want to test the default quota plugin.
    """
    assert context.persona
    import core.models
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


@step('we create an active instance')
def create_active_instance(context):
    assert context.persona
    user = context.persona['user']
    user_identity = context.persona['user_identity']
    provider_machine = context.persona['provider_machine']

    active_instance = api.tests.factories.InstanceFactory.create(name='Instance in active', provider_alias=uuid.uuid4(),
                                                                 source=provider_machine.instance_source,
                                                                 created_by=user,
                                                                 created_by_identity=user_identity,
                                                                 start_date=django.utils.timezone.now())

    active_status = api.tests.factories.InstanceStatusFactory.create(name='active')
    api.tests.factories.InstanceHistoryFactory.create(
        status=active_status,
        activity='',
        instance=active_instance
    )

    context.persona['active_instance'] = active_instance


@when('we get the details for the active instance via the API')
def step_impl(context):
    assert context.persona
    client = context.persona['client']
    active_instance = context.persona['active_instance']
    url = django.urls.reverse('api:v2:instance-detail',
                              args=(active_instance.provider_alias,))
    context.persona['response'] = client.get(url)
    context.persona['provider_alias'] = context.persona['response'].data['version']['id']


@step('the API response code is {response_code:d}')
def api_response_code_is(context, response_code):
    assert context.persona
    assert isinstance(context.test, unittest.case.TestCase)
    context.test.assertEqual(context.persona['response'].status_code, response_code)


@step('a dummy browser')
def dummy_browser(context):
    context.single_browser = True
    context.browser = 'dummy'
    context.is_connected = True
