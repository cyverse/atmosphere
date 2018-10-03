from django.test import TestCase, override_settings
import mock

from core.email import resource_request_email, email_admin, email_from_admin
from api.tests.factories import UserFactory


class EmailTests(TestCase):
    def test_resource_request_email(self):
        """
        Assert general expected behavior of resource_request_email
        """
        user = UserFactory(
            username="user0",
            first_name="First",
            last_name="Last",
            email="first@site.com"
        )

        # Mock out a request
        request = mock.Mock()
        request.user = user
        request.POST = {}
        request.session = None

        with mock.patch('core.tasks.EmailMessage') as MockMessage, \
                override_settings(ATMO_SUPPORT=('Support', 'support@email.com')):
            resource_request_email(
                request, user.username, "All the resources", "Did I stutter?"
            )
            kwargs = MockMessage.call_args[1]

            # Assert that Django's EmailMessage is called with the right
            # paramaters
            # Note: We are not testing the body of the email here
            MockMessage.assert_called_with(
                cc=None,
                to=['Support <support@email.com>'],
                subject='Atmosphere Resource Request - user0',
                from_email='First Last <first@site.com>',
                body=kwargs['body']
            )

    def test_email_admin(self):
        """
        Assert that emails to admin correctly set from, to, and cc fields
        """
        with mock.patch('core.tasks.EmailMessage') as MockMessage, \
                override_settings(ADMINS=[
                    ('Admin1', 'admin1@email.com'),
                    ('Admin2', 'admin2@email.com')]):
            email_admin('Subject', 'Body', 'First Last <first@site.com>')
            kwargs = MockMessage.call_args[1]

            MockMessage.assert_called_with(
                to=['Admin1 <admin1@email.com>', 'Admin2 <admin2@email.com>'],
                from_email='First Last <first@site.com>',
                cc=None,
                subject=kwargs['subject'],
                body=kwargs['body'],
            )

    def test_email_from_admin(self):
        """
        Assert that emails from admin to user correctly set from, to, and cc fields
        """
        UserFactory(
            username="user0",
            first_name="First",
            last_name="Last",
            email="first@site.com"
        )
        with mock.patch('core.tasks.EmailMessage') as MockMessage, \
                override_settings(ATMO_DAEMON=('AtmoAdmin', 'admin@local.atmo.cloud')):
            email_from_admin("user0", 'Subject', 'Body')
            kwargs = MockMessage.call_args[1]

            MockMessage.assert_called_with(
                to=['First Last <first@site.com>'],
                from_email='AtmoAdmin <admin@local.atmo.cloud>',
                cc=['AtmoAdmin <admin@local.atmo.cloud>'],
                subject=kwargs['subject'],
                body=kwargs['body'],
            )
