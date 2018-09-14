from django.urls import reverse
from rest_framework.test import APIRequestFactory
from rest_framework.test import APITestCase, force_authenticate

from api.tests.v2.base import APISanityTestCase
from api.v2.views import ResourceRequestViewSet, AdminResourceRequestViewSet
from core.models import ResourceRequest, StatusType, AtmosphereUser


class ResourceRequestSanityTests(APITestCase, APISanityTestCase):
    url_route = 'api:v2:resourcerequest'

    def setUp(self):
        self.list_view = ResourceRequestViewSet.as_view({'get': 'list'})
        self.user = AtmosphereUser.objects.create(username='user')


class UserResourceRequestTests(APITestCase):
    def test_list_user_resource_requests(self):
        """
        Users shouldn't see other users resource requests
        """
        # Create a request owned by a user
        user_a = AtmosphereUser.objects.create(username='user_a')
        create_request_for_user(user_a)

        # Create a request owned by a user
        user_b = AtmosphereUser.objects.create(username='user_b')
        create_request_for_user(user_b)

        # Fetch user_a's requests from api
        url = reverse('api:v2:resourcerequest-list')
        view = ResourceRequestViewSet.as_view({'get': 'list'})
        factory = APIRequestFactory()
        request = factory.get(url)
        force_authenticate(request, user=user_a)
        response = view(request)

        # The resource requests returned were created by user_a
        for resource_request in response.data["results"]:
            self.assertEqual(
                resource_request["created_by"]["username"], user_a.username
            )

    def test_user_not_allowed_to_approve(self):
        """
        Users cannot approve their own requests
        """
        update_status, _ = StatusType.objects.get_or_create(name='approved')
        response = submit_patch_with_payload(
            {
                'status': {
                    'id': update_status.pk
                }
            }
        )
        self.assertEqual(response.status_code, 403)

    def test_user_not_allowed_to_deny(self):
        """
        Users cannot deny their own requests
        """
        update_status, _ = StatusType.objects.get_or_create(name='denied')
        response = submit_patch_with_payload(
            {
                'status': {
                    'id': update_status.pk
                }
            }
        )
        self.assertEqual(response.status_code, 403)

    def test_user_closing_their_request(self):
        """
        Users can close their own requests
        """
        user = AtmosphereUser.objects.create(username='user')
        resource_request = create_request_for_user(user)
        update_status, _ = StatusType.objects.get_or_create(name='closed')

        # Close their request
        response = submit_patch_with_payload(
            {
                'status': {
                    'id': update_status.pk
                }
            },
            user=user,
            resource_request=resource_request
        )

        # Assert api success
        self.assertEqual(response.status_code, 200)

        # Assert that the resource request was actually closed
        updated_resource_request = ResourceRequest.objects.get(
            pk=resource_request.pk
        )
        self.assertEqual(
            updated_resource_request.status.name, update_status.name
        )

    def test_user_cannot_update_admin_message(self):
        """
        Users cannot update the admin message of their request
        """
        user = AtmosphereUser.objects.create(username='user')
        resource_request = create_request_for_user(user)

        # Attempt to update the admin message
        response = submit_patch_with_payload(
            {
                "admin_message": "idk why anyone would do this"
            },
            user=user,
            resource_request=resource_request
        )

        # Assert that they don't have permission
        self.assertEqual(response.status_code, 403)

        # Assert that the resource request wasn't changed
        updated_resource_request = ResourceRequest.objects.get(
            pk=resource_request.pk
        )
        self.assertEqual(
            updated_resource_request.admin_message,
            resource_request.admin_message
        )

    def test_user_can_submit_resource_request(self):
        """
        Users cannot update the admin message of their request
        """
        user = AtmosphereUser.objects.create(username='user')
        url = reverse('api:v2:resourcerequest-list')
        view = ResourceRequestViewSet.as_view({'post': 'create'})
        factory = APIRequestFactory()
        request = factory.post(
            url, {
                'request':
                    "100000 AU",
                'description':
                    'Make world better place',
                'admin_url':
                    'https://local.atmo.cloud/application/admin/resource_requests/'
            }
        )
        force_authenticate(request, user=user)
        response = view(request)

        # Response indicated creation
        self.assertEqual(response.status_code, 201)


class AdminResourceRequestTests(APITestCase):
    def test_staff_can_approve(self):
        """
        Admins can approve users' requests
        """
        user = AtmosphereUser.objects.create(username='user')
        resource_request = create_request_for_user(user)
        update_status, _ = StatusType.objects.get_or_create(name='approved')
        staff_user = AtmosphereUser.objects.create(
            username='staff_user', is_staff=True
        )

        # Approve user request
        response = submit_patch_with_payload(
            {
                'status': {
                    'id': update_status.pk
                }
            },
            user=staff_user,
            resource_request=resource_request,
            view_path='api:v2:admin:resourcerequest-detail',
            viewset=AdminResourceRequestViewSet
        )

        # Assert api success
        self.assertEqual(response.status_code, 200)

        # Assert that the resource request was actually approved
        updated_resource_request = ResourceRequest.objects.get(
            pk=resource_request.pk
        )
        self.assertEqual(
            updated_resource_request.status.name, update_status.name
        )


def create_request_for_user(user):
    status, _ = StatusType.objects.get_or_create(name='pending')
    return ResourceRequest.objects.create(
        created_by=user, description="test", status=status, request="test"
    )


def submit_patch_with_payload(
    payload,
    user=None,
    resource_request=None,
    view_path='api:v2:resourcerequest-detail',
    viewset=ResourceRequestViewSet
):
    """
    Submits a patch to update the a user and their resource request.
    Returns the response.
    """
    if not user:
        user = AtmosphereUser.objects.create(username='user')

    if not resource_request:
        resource_request = create_request_for_user(user)

    url = reverse(view_path, args=[resource_request.pk])
    view = viewset.as_view({'patch': 'partial_update'})

    request = APIRequestFactory().patch(url, payload, format='json')
    force_authenticate(request, user=user)

    response = view(request, pk=resource_request.pk)
    return response
