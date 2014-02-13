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

from api import failureJSON, prepare_driver


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
        data = {
            'provider': reverse('provider-list',
                                request=request),
            'identity': reverse('identity-list',
                                args=(provider_id,),
                                request=request),
            'volume': reverse('volume-list',
                              args=(provider_id, identity_id),
                              request=request),
            'meta': reverse('meta-detail',
                            args=(provider_id, identity_id),
                            request=request),
            'instance': reverse('instance-list',
                                args=(provider_id, identity_id),
                                request=request),
            'machine': reverse('machine-list',
                               args=(provider_id, identity_id),
                               request=request),
            'size': reverse('size-list',
                            args=(provider_id, identity_id),
                            request=request),
            'profile': reverse('profile', request=request)
        }
        return Response(data)


class MetaAction(APIView):
    """
    Atmosphere service meta rest api.
    """
    @api_auth_token_required
    def get(self, request, provider_id, identity_id, action=None):
        """
        """
        if not action:
            errorObj = failureJSON([{
                'code': 400,
                'message': 'Action is not supported.'}])
            return Response(errorObj, status=status.HTTP_400_BAD_REQUEST)
        esh_driver = prepare_driver(request, provider_id, identity_id)
        esh_meta = esh_driver.meta()
        try:
            if 'test_links' in action:
                test_links = esh_meta.test_links()
                return Response(test_links, status=status.HTTP_200_OK)
        except InvalidCredsError:
            logger.warn('Authentication Failed. Provider-id:%s Identity-id:%s'
                        % (provider_id, identity_id))
            errorObj = failureJSON([{
                'code': 401,
                'message': 'Identity/Provider Authentication Failed'}])
            return Response(errorObj, status=status.HTTP_401_UNAUTHORIZED)
        except NotImplemented, ne:
            logger.exception(ne)
            errorObj = failureJSON([{
                'code': 404,
                'message':
                'The requested resource %s is not available on this provider'
                % action}])
            return Response(errorObj, status=status.HTTP_404_NOT_FOUND)
