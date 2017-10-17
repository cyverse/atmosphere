import unittest

from django.utils.timezone import now

from core.tests.helpers import CoreApplicationHelper
from core.models import (AtmosphereUser, MatchType, PatternMatch)


class CoreApplicationTestCase(unittest.TestCase):

    def assertAccessList(self, expected_result):
        usernames = self.calculate_valid_usernames()
        return self.assertTrue(usernames == expected_result, "%s != ExpectedResult(%s)" % (usernames, expected_result))

    def calculate_valid_usernames(self):
        allowed_users = self.app.get_users_from_access_list()
        usernames = sorted(allowed_users.values_list('username', flat=True))
        return usernames


class TestApplicationAccessList(CoreApplicationTestCase):
    """
    Todo: Additional test cases using:
    - Wildcards, comma-separated usernames
    - Mix of email/user
    """

    def setUp(self):
        self.app_helper = CoreApplicationHelper(
            "Pattern Match app test", now())
        self.app = self.app_helper.application
        self._prepare_patterns()
        self._prepare_users()

    def _prepare_users(self):
        AtmosphereUser.objects.get_or_create(
            username='cdosborn', email="cdosborn@test.email.com")
        AtmosphereUser.objects.get_or_create(
            username='lenards', email="lenards@test.email.com")
        AtmosphereUser.objects.get_or_create(
            username='sgregory', email="steve-gregory@test.email.com")
        AtmosphereUser.objects.get_or_create(
            username='steve', email="steve-gregory2@test.email.com")
        AtmosphereUser.objects.get_or_create(
            username='gmail_user', email="test_user@gmail.com")
        AtmosphereUser.objects.get_or_create(
            username='cyversedemo1', email="cyversedemo1@test.email.com")
        AtmosphereUser.objects.get_or_create(
            username='cyversedemo2', email="cyversedemo2@test.email.com")
        AtmosphereUser.objects.get_or_create(
            username='cyversedemo3', email="cyversedemo3@test.email.com")
        return

    def _prepare_patterns(self):
        atmosphere_user = self.app_helper.user
        email_type = MatchType.objects.get_or_create(name='Email')[0]
        user_type = MatchType.objects.get_or_create(name='Username')[0]
        self.deny_wildcard_usernames = PatternMatch.objects.get_or_create(
            pattern="s*",
            type=user_type,
            created_by=atmosphere_user,
            allow_access=False)[0]
        self.deny_specific_usernames = PatternMatch.objects.get_or_create(
            pattern="sgregory,steve",
            type=user_type,
            created_by=atmosphere_user,
            allow_access=False)[0]
        self.deny_specific_test_email = PatternMatch.objects.get_or_create(
            pattern="steve-gregory@test.email.com",
            type=email_type,
            created_by=atmosphere_user,
            allow_access=False)[0]
        self.allow_lenards = PatternMatch.objects.get_or_create(
            pattern="lenards",
            type=user_type,
            created_by=atmosphere_user,
            allow_access=True)[0]
        self.allow_cdosborn = PatternMatch.objects.get_or_create(
            pattern="cdosborn",
            type=user_type,
            created_by=atmosphere_user,
            allow_access=True)[0]
        self.allow_cyverse_demos = PatternMatch.objects.get_or_create(
            pattern="cyversedemo*",
            type=user_type,
            created_by=atmosphere_user,
            allow_access=True)[0]
        self.allow_test_email = PatternMatch.objects.get_or_create(
            pattern="*@test.email.com",
            type=email_type,
            created_by=atmosphere_user,
            allow_access=True)[0]
        return

    def test_deny_allow_logic(self):
        # In this test, we expect the same result as above.
        # Atmosphere will always apply logic as: 'Allow..' then 'Deny..'
        self.app.access_list.add(self.deny_specific_test_email)
        self.app.access_list.add(self.allow_test_email)
        expected_result = [
            u'cdosborn', u'cyversedemo1', u'cyversedemo2',
            u'cyversedemo3', u'lenards', u'steve']
        self.assertAccessList(expected_result)
        self.app.access_list.clear()

    def test_simple_access(self):
        """
        Assert that the instance has only ONE history
        """
        self.app.access_list.add(self.allow_cdosborn)
        expected_result = [u'cdosborn']
        self.assertAccessList(expected_result)
        self.app.access_list.clear()

        self.app.access_list.add(self.allow_lenards)
        expected_result = [u'lenards']
        self.assertAccessList(expected_result)
        self.app.access_list.clear()

        self.app.access_list.add(self.allow_cyverse_demos)
        expected_result = [
            u'cyversedemo1', u'cyversedemo2', u'cyversedemo3']
        self.assertAccessList(expected_result)
        self.app.access_list.clear()

        self.app.access_list.add(self.allow_test_email)
        expected_result = [
            u'cdosborn', u'cyversedemo1', u'cyversedemo2',
            u'cyversedemo3', u'lenards', u'steve']
        self.assertAccessList(expected_result)
        self.app.access_list.clear()

    def test_allow_deny_logic(self):
        self.app.access_list.add(self.allow_test_email)
        self.app.access_list.add(self.deny_specific_test_email)
        expected_result = [
            u'cdosborn', u'cyversedemo1', u'cyversedemo2',
            u'cyversedemo3', u'lenards']
        self.assertAccessList(expected_result)
        self.app.access_list.clear()

    def test_multiple_allow_logic(self):
        self.app.access_list.add(self.allow_cyverse_demos)
        self.app.access_list.add(self.allow_cdosborn)
        self.app.access_list.add(self.allow_lenards)
        expected_result = [
            u'cdosborn', u'cyversedemo1', u'cyversedemo2',
            u'cyversedemo3', u'lenards']
        self.assertAccessList(expected_result)
        self.app.access_list.clear()
