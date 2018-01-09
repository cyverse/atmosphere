from rest_framework.test import APITestCase, APIRequestFactory,\
    force_authenticate
from api.v2.views import ImageBookmarkViewSet as ViewSet
from .base import APISanityTestCase
from api.tests.factories import (
    AnonymousUserFactory,
    ApplicationVersionFactory,
    ProviderFactory,
    IdentityFactory,
    ImageFactory,
    ImageBookmarkFactory,
    ProviderMachineFactory,
    UserFactory
)
from django.core.urlresolvers import reverse
from django.utils import timezone

EXPECTED_FIELD_COUNT = 14


class ApplicationBookmarkTests(APITestCase, APISanityTestCase):
    url_route = 'api:v2:applicationbookmark'

    def tearDown(self):
        self.user.delete()
        self.provider.delete()

    def setUp(self):
        factory = APIRequestFactory()
        # Create some users
        self.anonymous_user = AnonymousUserFactory()
        self.author = UserFactory.create(username="author")
        self.random_user = UserFactory.create(username="So-Random")
        self.user = self.author
        # Create some Identities for the users
        self.provider = ProviderFactory.create()
        self.author_identity = IdentityFactory.create_identity(
            created_by=self.author,
            provider=self.provider)

        self.random_identity = IdentityFactory.create_identity(
            created_by=self.random_user,
            provider=self.provider)

        # Create some images for the identities
        self.private_image = ImageFactory.create(
            name="Private image",
            created_by=self.author,
            private=True)
        self.private_version = ApplicationVersionFactory.create_version(
            self.author, self.author_identity,
            application=self.private_image
        )
        self.private_machine = ProviderMachineFactory.create_provider_machine(
            self.author, self.author_identity,
            application=self.private_image,
            version=self.private_version)

        end_date = timezone.now() - timezone.timedelta(hours=24)
        self.end_dated_image = ImageFactory.create(
            name="End-dated image",
            created_by=self.author,
            private=False,
            end_date=end_date)
        self.end_dated_version = ApplicationVersionFactory.create_version(
            self.author, self.author_identity,
            application=self.end_dated_image,
            end_date=end_date
        )
        self.end_dated_machine = ProviderMachineFactory.create_provider_machine(
            self.author, self.author_identity,
            application=self.end_dated_image,
            version=self.end_dated_version,
            end_date=end_date)

        self.public_image = ImageFactory.create(
            name="Public image",
            created_by=self.author,
            private=False)
        self.public_version = ApplicationVersionFactory.create_version(
            self.author, self.author_identity,
            application=self.public_image
        )
        self.public_machine = ProviderMachineFactory.create_provider_machine(
            self.author, self.author_identity,
            application=self.public_image,
            version=self.public_version)

        # Create some ImageBookmarks
        self.old_bookmark_for_random_user = ImageBookmarkFactory.create(
            application=self.end_dated_image,
            user=self.random_user)
        self.old_bookmark_for_author = ImageBookmarkFactory.create(
            application=self.end_dated_image,
            user=self.author)

        self.bookmark_for_random_user = ImageBookmarkFactory.create(
            application=self.public_image,
            user=self.random_user)
        self.bookmark_for_author = ImageBookmarkFactory.create(
            application=self.public_image,
            user=self.author)

        self.list_view = ViewSet.as_view({'get': 'list'})
        list_url = reverse(self.url_route+'-list')
        self.list_request = factory.get(list_url)

    def test_list_is_visible_to_author(self):
        force_authenticate(self.list_request, user=self.author)
        response = self.list_view(self.list_request)
        self.assertEquals(response.status_code, 200)
        self.assertIn(
            "results", response.data,
            "Invalid response(%s): %s" % (response.status_code, response.data))
        results = response.data['results']
        self.assertEquals(
            len(results), 1,
            "Expected exactly one bookmark, found %s" % len(results))
        for result in results:
            self.assertIn('user', result)
            user = result['user']
            self.assertIn('username', user)
            username = user['username']
            self.assertEquals(
                username, self.author.username,
                "Expected bookmark to belong to self.author.username(%s). Found %s"
                % (self.author.username, username))

    def test_list_is_visible_to_random_user(self):
        force_authenticate(self.list_request, user=self.random_user)
        response = self.list_view(self.list_request)
        self.assertEquals(response.status_code, 200)
        self.assertIn(
            "results", response.data,
            "Invalid response(%s): %s" % (response.status_code, response.data))
        results = response.data['results']
        self.assertEquals(
            len(results), 1,
            "Expected exactly one bookmark, found %s" % len(results))
        for result in results:
            self.assertIn('user', result)
            user = result['user']
            self.assertIn('username', user)
            username = user['username']
            self.assertEquals(
                username, self.random_user.username,
                "Expected bookmark to belong to self.random_user.username(%s). Found %s"
                % (self.random_user.username, username))
