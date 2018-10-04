from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate
import mock

from api.v2.views import (
    VolumeSupportEmailViewSet, InstanceSupportEmailViewSet,
    FeedbackEmailViewSet, ResourceEmailViewSet
)
from api.tests.factories import (
    AnonymousUserFactory, InstanceFactory, UserFactory, VolumeFactory
)


class VolumeEmailTests(TestCase):
    def setUp(self):
        volume = VolumeFactory.create(
            name="Volume", description="Test volume", size=1
        )
        self.request = APIRequestFactory().post(
            'api:v2:email_volume_report', {
                'message': 'test message',
                'volume': volume.id
            }
        )
        self.request.POST._mutable = True
        self.view = VolumeSupportEmailViewSet.as_view({'post': 'create'})

    def test_volume_support_email(self):
        force_authenticate(self.request, user=UserFactory())
        with mock.patch(
            "api.v2.views.email.email_support"
        ) as mock_email_support:
            response = self.view(self.request)
            mock_email_support.assert_called_once()
            self.assertEquals(response.status_code, 200)

    def test_anonymous_volume_support_email(self):
        force_authenticate(self.request, user=AnonymousUserFactory())
        with mock.patch(
            "api.v2.views.email.email_support"
        ) as mock_email_support:
            response = self.view(self.request)
            mock_email_support.assert_not_called()
            self.assertEquals(response.status_code, 403)


class InstanceEmailTests(TestCase):
    def setUp(self):
        instance = InstanceFactory.create()
        self.request = APIRequestFactory().post(
            'api:v2:email_instance_report', {
                'message': 'test message',
                'instance': instance.id
            }
        )
        self.request.POST._mutable = True
        self.view = InstanceSupportEmailViewSet.as_view({'post': 'create'})

    def test_instance_support_email(self):
        force_authenticate(self.request, user=UserFactory())
        with mock.patch(
            "api.v2.views.email.email_support"
        ) as mock_email_support:
            response = self.view(self.request)
            mock_email_support.assert_called_once()
            self.assertEquals(response.status_code, 200)

    def test_anonymous_instance_support_email(self):
        force_authenticate(self.request, user=AnonymousUserFactory())
        with mock.patch(
            "api.v2.views.email.email_support"
        ) as mock_email_support:
            response = self.view(self.request)
            mock_email_support.assert_not_called()
            self.assertEquals(response.status_code, 403)


class FeedbackEmailTests(TestCase):
    def setUp(self):
        self.request = APIRequestFactory().post(
            'api:v2:email_feedback', {
                'message': 'test message',
            }
        )
        self.request.POST._mutable = True
        self.view = FeedbackEmailViewSet.as_view({'post': 'create'})

    def test_feedback_email(self):
        force_authenticate(self.request, user=UserFactory())
        with mock.patch(
            "api.v2.views.email.email_support"
        ) as mock_email_support:
            response = self.view(self.request)
            mock_email_support.assert_called_once()
            self.assertEquals(response.status_code, 200)

    def test_anonymous_feedback_email(self):
        force_authenticate(self.request, user=AnonymousUserFactory())
        with mock.patch(
            "api.v2.views.email.email_support"
        ) as mock_email_support:
            response = self.view(self.request)
            mock_email_support.assert_not_called()
            self.assertEquals(response.status_code, 403)


class ResourceEmailTests(TestCase):
    def setUp(self):
        self.request = APIRequestFactory().post(
            'api:v2:email_request_resources', {
                'quota': 'big things',
                'reason': 'pls'
            }
        )
        self.request.POST._mutable = True
        self.view = ResourceEmailViewSet.as_view({'post': 'create'})

    def test_resource_email(self):
        force_authenticate(self.request, user=UserFactory())
        with mock.patch(
            "api.v2.views.email.resource_request_email"
        ) as mock_email_support:
            response = self.view(self.request)
            mock_email_support.assert_called_once()
            self.assertEquals(response.status_code, 200)

    def test_anonymous_resource_email(self):
        force_authenticate(self.request, user=AnonymousUserFactory())
        with mock.patch(
            "api.v2.views.email.resource_request_email"
        ) as mock_email_support:
            response = self.view(self.request)
            mock_email_support.assert_not_called()
            self.assertEquals(response.status_code, 403)
