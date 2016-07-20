"""
Atmosphere service meta rest api.

"""
from datetime import datetime
import time

from rtwo.exceptions import LibcloudInvalidCredsError

from rest_framework import status
from rest_framework.response import Response
from rest_framework.reverse import reverse

from threepio import logger

from service.driver import prepare_driver

from api import failure_response, invalid_creds
from api.exceptions import inactive_provider
from core.exceptions import ProviderNotActive
from api.v1.views.base import AuthAPIView


class Meta(AuthAPIView):

    """
    Meta-details about Atmosphere API, including self-describing URLs.
    """

    def get(self, request, provider_uuid, identity_uuid):
        """
        Returns all available URLs based on the user profile.
        """
        try:
            esh_driver = prepare_driver(request, provider_uuid, identity_uuid)
        except ProviderNotActive as pna:
            return inactive_provider(pna)
        except Exception as e:
            return failure_response(
                status.HTTP_409_CONFLICT,
                e.message)

        if not esh_driver:
            return invalid_creds(provider_uuid, identity_uuid)
        data = add_user_urls(request, provider_uuid, identity_uuid)
        if request.user.is_staff:
            add_staff_urls(request, provider_uuid, identity_uuid)
        return Response(data)


def add_staff_urls(request, provider_uuid, identity_uuid):
    data = {
        'request-image-list':
        reverse('api:v1:direct-machine-request-list',
                request=request), }


def add_user_urls(request, provider_uuid, identity_uuid):
    data = {
        'group-list': reverse('api:v1:group-list',
                              request=request),
        'tag-list': reverse('api:v1:tag-list',
                            request=request),
        'provider-list': reverse('api:v1:provider-list',
                                 request=request),
        'occupancy': reverse('api:v1:occupancy',
                             args=(provider_uuid,),
                             request=request),
        'hypervisor': reverse('api:v1:hypervisor',
                              args=(provider_uuid,),
                              request=request),
        'identity-list': reverse('api:v1:identity-list',
                                 args=(provider_uuid,),
                                 request=request),
        'volume-list': reverse('api:v1:volume-list',
                               args=(provider_uuid, identity_uuid),
                               request=request),
        'meta': reverse('api:v1:meta-detail',
                        args=(provider_uuid, identity_uuid),
                        request=request),
        'machine-history-list': reverse('api:v1:machine-history',
                                        args=(provider_uuid, identity_uuid),
                                        request=request),
        'instance-history-list': reverse('api:v1:instance-history',
                                         args=(provider_uuid, identity_uuid),
                                         request=request),
        'instance-list': reverse('api:v1:instance-list',
                                 args=(provider_uuid, identity_uuid),
                                 request=request),
        'machine-list': reverse('api:v1:machine-list',
                                args=(provider_uuid, identity_uuid),
                                request=request),
        'size-list': reverse('api:v1:size-list',
                             args=(provider_uuid, identity_uuid),
                             request=request),
        'profile': reverse('api:v1:profile', request=request)}
    return data


class MetaAction(AuthAPIView):

    """
    Atmosphere service meta rest api.
    """

    def get(self, request, provider_uuid, identity_uuid, action=None):
        """
        """
        if not action:
            return failure_response(
                status.HTTP_400_BAD_REQUEST,
                'Action is not supported.'
            )
        try:
            esh_driver = prepare_driver(request, provider_uuid, identity_uuid)
        except ProviderNotActive as pna:
            return inactive_provider(pna)
        except Exception as e:
            return failure_response(
                status.HTTP_409_CONFLICT,
                e.message)
        if not esh_driver:
            return invalid_creds(provider_uuid, identity_uuid)
        esh_meta = esh_driver.meta()
        try:
            if 'test_links' in action:
                test_links = esh_meta.test_links()
                return Response(test_links, status=status.HTTP_200_OK)
        except LibcloudInvalidCredsError:
            logger.warn('Authentication Failed. Provider-id:%s Identity-id:%s'
                        % (provider_uuid, identity_uuid))
            return failure_response(
                status.HTTP_401_UNAUTHORIZED,
                'Identity/Provider Authentication Failed')
        except NotImplemented as ne:
            logger.exception(ne)
            return failure_response(
                status.HTTP_404_NOT_FOUND,
                'The requested resource %s is not available on this provider'
                % action)
