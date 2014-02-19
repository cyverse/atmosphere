"""
Atmosphere service meta rest api.

"""
from datetime import datetime
import time

from libcloud.common.types import InvalidCredsError

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.reverse import reverse

from threepio import logger

from authentication.decorators import api_auth_token_required

from api import failure_response, prepare_driver, invalid_creds


class Meta(APIView):
    """
    Atmosphere service meta rest api.
    """
    @api_auth_token_required
    def get(self, request, provider_id, identity_id):
        """
        Returns all available URLs based on the user profile.
        """
        esh_driver = prepare_driver(request, provider_id, identity_id)
        if not esh_driver:
            return invalid_creds(provider_id, identity_id)
        data = add_user_urls(request, provider_id, identity_id)
        if request.user.is_staff:
            add_staff_urls(request, provider_id, identity_id)
        return Response(data)


def add_staff_urls(request, provider_id, identity_id):
    data = {
        'request-image-list': reverse('direct-machine-request-list',
                            request=request),
        }
def add_user_urls(request, provider_id, identity_id):
    data = {
        'group-list': reverse('group-list',
                            request=request),
        'tag-list': reverse('tag-list',
                            request=request),
        'provider-list': reverse('provider-list',
                            request=request),
        'occupancy': reverse('occupancy',
                            args=(provider_id,),
                            request=request),
        'hypervisor': reverse('hypervisor',
                            args=(provider_id,),
                            request=request),
        'identity-list': reverse('identity-list',
                            args=(provider_id,),
                            request=request),
        'volume-list': reverse('volume-list',
                          args=(provider_id, identity_id),
                          request=request),
        'meta': reverse('meta-detail',
                        args=(provider_id, identity_id),
                        request=request),
        'machine-history-list': reverse('machine-history',
                            args=(provider_id, identity_id),
                            request=request),
        'instance-history-list': reverse('instance-history',
                            args=(provider_id, identity_id),
                            request=request),
        'instance-list': reverse('instance-list',
                            args=(provider_id, identity_id),
                            request=request),
        'machine-list': reverse('machine-list',
                           args=(provider_id, identity_id),
                           request=request),
        'size-list': reverse('size-list',
                        args=(provider_id, identity_id),
                        request=request),
        'profile': reverse('profile', request=request)
    }
    return data

class MetaAction(APIView):
    """
    Atmosphere service meta rest api.
    """
    @api_auth_token_required
    def get(self, request, provider_id, identity_id, action=None):
        """
        """
        if not action:
            return failure_response(
                status.HTTP_400_BAD_REQUEST,
                'Action is not supported.'
            )
        esh_driver = prepare_driver(request, provider_id, identity_id)
        if not esh_driver:
            return invalid_creds(provider_id, identity_id)
        esh_meta = esh_driver.meta()
        try:
            if 'test_links' in action:
                test_links = esh_meta.test_links()
                return Response(test_links, status=status.HTTP_200_OK)
        except InvalidCredsError:
            logger.warn('Authentication Failed. Provider-id:%s Identity-id:%s'
                        % (provider_id, identity_id))
            return failure_response(
                status.HTTP_401_UNAUTHORIZED,
                'Identity/Provider Authentication Failed')
        except NotImplemented, ne:
            logger.exception(ne)
            return failure_response(
                status.HTTP_404_NOT_FOUND,
                'The requested resource %s is not available on this provider'
                % action)
