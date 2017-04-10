import uuid

from django.core.urlresolvers import reverse
from django.utils import timezone

from rest_framework.test import APITestCase, APIRequestFactory, force_authenticate

from api.tests.factories import (
    GroupFactory, UserFactory, AnonymousUserFactory, InstanceFactory, InstanceHistoryFactory, InstanceStatusFactory,
    ImageFactory, ApplicationVersionFactory, InstanceSourceFactory, ProviderMachineFactory, IdentityFactory,
    ProviderFactory, IdentityMembershipFactory, ProjectFactory, ProjectInstanceFactory, LeadershipFactory)

from api.v2.views import ProjectInstanceViewSet
from core.models import AtmosphereUser, Group

class GetProjectInstanceListTests(APITestCase):
    def setUp(self):
        self.anonymous_user = AnonymousUserFactory()
        self.user = UserFactory.create(username='test-username')
        self.provider = ProviderFactory.create()
        self.user_identity = IdentityFactory.create_identity(
            created_by=self.user,
            provider=self.provider)
        self.group = Group.objects.get(name=self.user)
        self.project = ProjectFactory.create(owner=self.group)
        self.leadership = LeadershipFactory.create(
            user=self.user,
            group=self.group
        )
        self.machine = ProviderMachineFactory.create_provider_machine(self.user, self.user_identity)
        self.active_instance = InstanceFactory.create(name="Instance in active",
                                   provider_alias=uuid.uuid4(),
                                   source=self.machine.instance_source,
                                   created_by=self.user,
                                   created_by_identity=self.user_identity,
                                   start_date=timezone.now())
        self.project_instances = ProjectInstanceFactory.create(project=self.project, instance=self.active_instance)
        self.view = ProjectInstanceViewSet.as_view({'get': 'list'})
        factory = APIRequestFactory()
        url = reverse('api:v2:projectinstance-list')
        url_proj = "?project__id=" + str(self.project.id)
        url += url_proj
        print url
        self.request = factory.get(url)

    def test_response_contains_expected_fields(self):
        force_authenticate(self.request, user=self.user)
        response = self.view(self.request)
        data = response.data.get('results')[0]

        self.assertEquals(response.status_code, 200)
        self.assertEquals(len(data), 4, "Number of fields does not match")
        self.assertEquals(data['id'], self.project_instances.id)
        self.assertIn('url', data)
