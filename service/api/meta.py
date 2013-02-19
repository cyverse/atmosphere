B"""
Atmosphere service meta rest api.

"""
import json

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
#from rest_framework.renderers import JSONRenderer,JSONPRenderer

from libcloud.common.types import InvalidCredsError

from atmosphere.logger import logger

from auth.decorators import api_auth_token_required

from core.models.profile import getDefaultIdentity

from service.meta import Meta

from service.api import failureJSON, prepareDriver

class Meta(APIView):
    """ 
    Atmosphere service meta rest api.
    """
    @api_auth_token_required
    def get(self, request, provider_id=None, identity_id=None):
        """
        """
        esh_driver = prepareDriver(request, identity_id)
        try:
            esh_meta = esh_driver.meta()
            esh_meta_data = {'driver': unicode(esh_meta.driver),
                             'identity': unicode(esh_meta.identity.user.username),
                             'provider' : unicode(esh_meta.provider.name)}
            logger.info(esh_meta_data)
            return Response(esh_meta_data, status=status.HTTP_200_OK)
        except InvalidCredsError, ice:
            logger.warn('Authentication Failed. Provider-id:%s Identity-id:%s' % (provider_id,identity_id))
            errorObj = failureJSON([{'code':401,'message':'Identity/Provider Authentication Failed'}])
            return Response(errorObj, status=status.HTTP_401_UNAUTHORIZED)
        except NotImplemented, ne:
            logger.warn(ne)
            errorObj = failureJSON([{'code':404, 'message':'The requested resource %s is not available on this provider' % params['action']}])
            return Response(errorObj, status=status.HTTP_404_NOT_FOUND)

class MetaAction(APIView):
    """ 
    Atmosphere service meta rest api.
    """
    @api_auth_token_required
    def get(self, request, provider_id=None, identity_id=None, action=None):
        """
        """
        if not action:
            errorObj = failureJSON([{'code':400, 'message':'Action is not supported.'}])
            return Response(errorObj, status=status.HTTP_400_BAD_REQUEST)
        esh_driver = prepareDriver(request, identity_id)
        esh_meta = esh_driver.meta()
        try:
            if 'test_links' in action:
                test_links = esh_meta.test_links()
                logger.debug(test_links)
                return Response(test_links, status=status.HTTP_200_OK)
        except InvalidCredsError, ice:
            logger.warn('Authentication Failed. Provider-id:%s Identity-id:%s' % (provider_id,identity_id))
            errorObj = failureJSON([{'code':401,'message':'Identity/Provider Authentication Failed'}])
            return Response(errorObj, status=status.HTTP_401_UNAUTHORIZED)
        except NotImplemented, ne:
            logger.warn(ne)
            errorObj = failureJSON([{'code':404, 'message':'The requested action %s is not available on this provider' % params['action']}])
            return Response(errorObj, status=status.HTTP_404_NOT_FOUND)
