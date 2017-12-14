from django.core.urlresolvers import reverse
from django.conf import settings
from django.test import override_settings

from rest_framework.test import APITestCase, APIRequestFactory, force_authenticate
from api.tests.factories import (
    UserFactory, AnonymousUserFactory, InstanceFactory,
    ProviderMachineFactory)
from api.v2.views import InstanceAccessViewSet

"""
Test cases for instance access.

- An 'active_instance' have been included in 'setUp'
- Several users available for different, scenarios
"""


class InstanceAccessTests(APITestCase):
    fixtures = ["core/fixtures/status_type.json"]

    def setUp(self):
        self.anonymous_user = AnonymousUserFactory()
        self.not_user = UserFactory.create(username='not-test-username')
        self.user = UserFactory.create(username='test-username')
        self.ignore_user = UserFactory.create(username='ignore-user')
        self.shared_user = UserFactory.create(username='shared-user')
        self.provider_machine = ProviderMachineFactory()
        self.active_instance = InstanceFactory(
            name="Instance in active",
            created_by=self.user,
            source=self.provider_machine.instance_source
        )
        self.list_access_view = InstanceAccessViewSet.as_view({
            'get': 'list',
            'post': 'create'
        })
        self.detail_access_view = InstanceAccessViewSet.as_view({
            'get': 'retrieve',
            'put': 'update',
            'patch': 'partial_update',
            'delete': 'destroy'
        })
        self.instance_access_url = reverse('api:v2:instanceaccess-list')

    def test_create_and_self_approved(self):
        """
        In this test, user has offered an instance access request,
        user attempts to approve instance access request and fails.
        """
        instance_access_uuid = self.test_create_instance_access_request()
        data = {"status": "approved"}
        instance_access_detail_url = reverse('api:v2:instanceaccess-detail', args=(instance_access_uuid,))
        factory = APIRequestFactory()
        request = factory.patch(instance_access_detail_url, data, format='json')
        force_authenticate(request, user=self.user)
        response = self.detail_access_view(request, pk=instance_access_uuid)
        self.assertEquals(
            response.status_code, 400,
            "Expected 400, Received (%s):%s"
            % (response.status_code, response.data))
        error_msg = response.data['status'][0]
        expected_error = "Only user %s can approve the request for Instance Access" % self.shared_user.username
        self.assertEqual(
            error_msg, expected_error,
            "Unexpected error_message changed: %s != '%s'"
            % (error_msg, expected_error))

    def test_create_and_unauthorized_approve(self):
        """
        In this test, user has offered an instance access request,
        Unauthorized user attempts to approve instance access request and fails.
        """
        instance_access_uuid = self.test_create_instance_access_request()
        data = {"status": "approved"}
        instance_access_detail_url = reverse('api:v2:instanceaccess-detail', args=(instance_access_uuid,))
        factory = APIRequestFactory()
        request = factory.patch(instance_access_detail_url, data, format='json')
        force_authenticate(request, user=self.not_user)
        response = self.detail_access_view(request, pk=instance_access_uuid)
        self.assertEquals(
            response.status_code, 404,
            "Expected 404, Received (%s):%s"
            % (response.status_code, response.data))
        error_msg = response.data['detail']
        expected_error = "Not found."
        self.assertEqual(
            error_msg, expected_error,
            "Unexpected status after update: %s != '%s'"
            % (error_msg, expected_error))

    def test_create_and_authorized_approve(self):
        """
        In this test, user has offered an instance access request,
        the shared user approves the instance access request and succeeds.
        """
        instance_access_uuid = self.test_create_instance_access_request()
        data = {"status": "approved"}
        instance_access_detail_url = reverse('api:v2:instanceaccess-detail', args=(instance_access_uuid,))
        factory = APIRequestFactory()
        request = factory.patch(instance_access_detail_url, data, format='json')
        force_authenticate(request, user=self.shared_user)
        response = self.detail_access_view(request, pk=instance_access_uuid)
        self.assertEquals(
            response.status_code, 200,
            "Expected 200, Received (%s):%s"
            % (response.status_code, response.data))
        status_name = str(response.data['status'])
        self.assertEqual(
            "approved", status_name,
            "Unexpected status after update: %s != 'approved'" % status_name
        )
        return instance_access_uuid

    def test_create_and_deny(self):
        """
        In this test, user has offered an instance access request,
        the shared user denies the instance access request.
        """
        instance_access_uuid = self.test_create_instance_access_request()
        data = {"status": "denied"}
        instance_access_detail_url = reverse('api:v2:instanceaccess-detail', args=(instance_access_uuid,))
        factory = APIRequestFactory()
        request = factory.patch(instance_access_detail_url, data, format='json')
        force_authenticate(request, user=self.shared_user)
        response = self.detail_access_view(request, pk=instance_access_uuid)
        self.assertEquals(
            response.status_code, 200,
            "Expected 200, Received (%s):%s"
            % (response.status_code, response.data))
        status_name = str(response.data['status'])
        self.assertEqual(
            "denied", status_name,
            "Unexpected status after update: %s != 'denied'" % status_name
        )

    def test_create_and_attempt_delete_by_share_user(self):
        """
        In this test, user has offered an instance access request,
        the shared user attempts to delete the instance access request and fails.
        """
        instance_access_uuid = self.test_create_instance_access_request()
        instance_access_detail_url = reverse('api:v2:instanceaccess-detail', args=(instance_access_uuid,))
        factory = APIRequestFactory()
        request = factory.delete(instance_access_detail_url, format='json')
        force_authenticate(request, user=self.shared_user)
        response = self.detail_access_view(request, pk=instance_access_uuid)
        self.assertEquals(
            response.status_code, 204,
            "Expected 204, Received (%s):%s"
            % (response.status_code, response.data))
        # Future lookup, post-delete
        detail_request = factory.get(instance_access_detail_url, format='json')
        force_authenticate(detail_request, user=self.shared_user)
        response = self.detail_access_view(detail_request, pk=instance_access_uuid)
        self.assertEquals(
            response.status_code, 404,
            "Expected 404, Received (%s):%s"
            % (response.status_code, response.data))

    def test_created_approved_and_self_delete(self):
        """
        In this test, user has offered an instance access request,
        instance access request has been approved,
        and user has chosen to delete it.
        As part of the deletion process, the user is removed from the instance.
        """
        instance_access_uuid = self.test_create_and_authorized_approve()
        instance_access_detail_url = reverse('api:v2:instanceaccess-detail', args=(instance_access_uuid,))
        factory = APIRequestFactory()
        request = factory.delete(instance_access_detail_url, format='json')
        force_authenticate(request, user=self.user)
        response = self.detail_access_view(request, pk=instance_access_uuid)
        self.assertEquals(
            response.status_code, 204,
            "Expected 204, Received (%s):%s"
            % (response.status_code, response.data))
        # Future lookup, post-delete
        detail_request = factory.get(instance_access_detail_url, format='json')
        force_authenticate(detail_request, user=self.shared_user)
        response = self.detail_access_view(detail_request, pk=instance_access_uuid)
        self.assertEquals(
            response.status_code, 404,
            "Expected 404, Received (%s):%s"
            % (response.status_code, response.data))

    def test_create_and_self_delete(self):
        """
        In this test, user has offered an instance access request, and chosen to delete it before it was shared.
        """
        instance_access_uuid = self.test_create_instance_access_request()
        instance_access_detail_url = reverse('api:v2:instanceaccess-detail', args=(instance_access_uuid,))
        factory = APIRequestFactory()
        request = factory.delete(instance_access_detail_url, format='json')
        force_authenticate(request, user=self.user)
        response = self.detail_access_view(request, pk=instance_access_uuid)
        self.assertEquals(
            response.status_code, 204,
            "Expected 204, Received (%s):%s"
            % (response.status_code, response.data))
        # Future lookup, post-delete
        detail_request = factory.get(instance_access_detail_url, format='json')
        force_authenticate(detail_request, user=self.shared_user)
        response = self.detail_access_view(detail_request, pk=instance_access_uuid)
        self.assertEquals(
            response.status_code, 404,
            "Expected 404, Received (%s):%s"
            % (response.status_code, response.data))

    @override_settings(AUTO_APPROVE_INSTANCE_ACCESS=False)
    def test_create_instance_access_request(self):
        """
        In this test, user has offered an instance access request to 'shared_user'
        """
        expected_user = self.shared_user.username
        data = {
            "instance": self.active_instance.provider_alias,
            "user": expected_user,
        }
        factory = APIRequestFactory()
        request = factory.post(self.instance_access_url, data, format='json')
        force_authenticate(request, user=self.user)
        response = self.list_access_view(request)
        data = response.data.get('result')
        self.assertEquals(
            response.status_code, 201,
            "Expected 201, Received (%s):%s"
            % (response.status_code, response.data))
        self.assertIn(
            "id", response.data,
            "`id` is not in response.data: %s"
            % (response.data,))
        self.assertIn(
            "instance", response.data,
            "`instance` is not in response.data: %s"
            % (response.data,))
        self.assertIn(
            "user", response.data,
            "`user` is not in response.data: %s"
            % (response.data))
        self.assertIn(
            "status", response.data,
            "`status` is not in response.data: %s"
            % (response.data))
        uuid = response.data['id']
        status_name = str(response.data['status'])
        user = response.data['user']
        instance = response.data['instance']
        expected_instance_id = str(self.active_instance.provider_alias)
        instance_id = str(instance['provider_alias'])
        username = str(user['username'])
        self.assertEqual(
            "pending", status_name,
            "Unexpected status : %s" % status_name
        )
        self.assertEquals(
            expected_instance_id, instance_id,
            "Unexpected instance: %s != %s"
            % (expected_instance_id, instance_id)
        )
        self.assertEqual(
            expected_user, username,
            "Unexpected user: %s" % username
        )
        return uuid

    def test_create_auto_approved_and_deny(self):
        """
        In this test:
        - Instance access request is auto-approved.
        - Later, the user wants to delete their access.
        """
        instance_access_uuid = self.test_create_instance_access_request()
        data = {"status": "denied"}
        instance_access_detail_url = reverse('api:v2:instanceaccess-detail', args=(instance_access_uuid,))
        factory = APIRequestFactory()
        request = factory.patch(instance_access_detail_url, data, format='json')
        force_authenticate(request, user=self.shared_user)
        response = self.detail_access_view(request, pk=instance_access_uuid)
        self.assertEquals(
            response.status_code, 200,
            "Expected 200, Received (%s):%s"
            % (response.status_code, response.data))
        status_name = str(response.data['status'])
        self.assertEqual(
            "denied", status_name,
            "Unexpected status after update: %s != 'denied'" % status_name
        )

    def test_create_auto_approved_and_shared_user_delete(self):
        """
        In this test:
        - Instance access request is auto approved
        - Later, the shared user wishes to delete the request.
        """
        instance_access_uuid = self.test_create_instance_access_request_auto_approved()
        instance_access_detail_url = reverse('api:v2:instanceaccess-detail', args=(instance_access_uuid,))
        factory = APIRequestFactory()
        request = factory.delete(instance_access_detail_url, format='json')
        force_authenticate(request, user=self.shared_user)
        response = self.detail_access_view(request, pk=instance_access_uuid)
        self.assertEquals(
            response.status_code, 204,
            "Expected 204, Received (%s):%s"
            % (response.status_code, response.data))
        # Future lookup, post-delete
        detail_request = factory.get(instance_access_detail_url, format='json')
        force_authenticate(detail_request, user=self.shared_user)
        response = self.detail_access_view(detail_request, pk=instance_access_uuid)
        self.assertEquals(
            response.status_code, 404,
            "Expected 404, Received (%s):%s"
            % (response.status_code, response.data))


    def test_create_auto_approved_and_self_delete(self):
        """
        In this test, user has offered an instance access request, and chosen to delete it before it was shared.
        """
        instance_access_uuid = self.test_create_instance_access_request_auto_approved()
        instance_access_detail_url = reverse('api:v2:instanceaccess-detail', args=(instance_access_uuid,))
        factory = APIRequestFactory()
        request = factory.delete(instance_access_detail_url, format='json')
        force_authenticate(request, user=self.user)
        response = self.detail_access_view(request, pk=instance_access_uuid)
        self.assertEquals(
            response.status_code, 204,
            "Expected 204, Received (%s):%s"
            % (response.status_code, response.data))
        # Future lookup, post-delete
        detail_request = factory.get(instance_access_detail_url, format='json')
        force_authenticate(detail_request, user=self.shared_user)
        response = self.detail_access_view(detail_request, pk=instance_access_uuid)
        self.assertEquals(
            response.status_code, 404,
            "Expected 404, Received (%s):%s"
            % (response.status_code, response.data))


    @override_settings(AUTO_APPROVE_INSTANCE_ACCESS=True)
    def test_create_instance_access_request_auto_approved(self):
        """
        In this test, user has offered an instance access request to 'shared_user'
        - The request will be automatically approved and access will be granted.
        """
        expected_user = self.shared_user.username
        data = {
            "instance": self.active_instance.provider_alias,
            "user": expected_user,
        }
        factory = APIRequestFactory()
        request = factory.post(self.instance_access_url, data, format='json')
        force_authenticate(request, user=self.user)
        response = self.list_access_view(request)
        data = response.data.get('result')
        self.assertEquals(
            response.status_code, 201,
            "Expected 201, Received (%s):%s"
            % (response.status_code, response.data))
        self.assertIn(
            "id", response.data,
            "`id` is not in response.data: %s"
            % (response.data,))
        self.assertIn(
            "instance", response.data,
            "`instance` is not in response.data: %s"
            % (response.data,))
        self.assertIn(
            "user", response.data,
            "`user` is not in response.data: %s"
            % (response.data))
        self.assertIn(
            "status", response.data,
            "`status` is not in response.data: %s"
            % (response.data))
        uuid = response.data['id']
        status_name = str(response.data['status'])
        user = response.data['user']
        instance = response.data['instance']
        expected_instance_id = str(self.active_instance.provider_alias)
        instance_id = str(instance['provider_alias'])
        username = str(user['username'])
        self.assertEqual(
            "approved", status_name,
            "Unexpected status : %s" % status_name
        )
        self.assertEquals(
            expected_instance_id, instance_id,
            "Unexpected instance: %s != %s"
            % (expected_instance_id, instance_id)
        )
        self.assertEqual(
            expected_user, username,
            "Unexpected user: %s" % username
        )
        return uuid
