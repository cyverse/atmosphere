"""
Atmosphere service instance rest api.

"""
from datetime import datetime

## Frameworks
from django.core.exceptions import ValidationError

from rest_framework.reverse import reverse
from rest_framework.views import APIView
from rest_framework.response import Response

## Atmosphere Libraries
from atmosphere.logger import logger

from auth.decorators import api_auth_token_required

from service.api.serializers import ProfileSerializer


class Profile(APIView):
    """ 
    An instance is a self-contained copy of a machine built to a specific size and hosted on a specific provider 
    """

    @api_auth_token_required
    def get(self, request, provider_id=None, identity_id=None):
        """
        """
        logger.info(request.user)
        user = request.user
        logger.debug(user.get_profile())
        serialized_data = ProfileSerializer(user.get_profile()).data
        response = Response(serialized_data)
        return response

    @api_auth_token_required
    def patch(self, request, provider_id=None, identity_id=None):
        """
        Update a users profile
        If VALID save the profile
        else raise ValidationError
        """
        logger.warn(request.DATA)
        user = request.user
        profile = user.get_profile()
        serializer = ProfileSerializer(profile, data=request.DATA, partial=True)
        if serializer.is_valid():
            serializer.save()
            response = Response(serializer.data)
            return response
        else:
            return Response(serializer.errors)

    @api_auth_token_required
    def put(self, request, provider_id=None, identity_id=None):
        """
        Update a users profile
        If VALID save the profile
        else raise ValidationError
        """
        logger.warn(request.DATA)
        user = request.user
        profile = user.get_profile()
        serializer = ProfileSerializer(profile, data=request.DATA)
        if serializer.is_valid():
            serializer.save()
            response = Response(serializer.data)
            return response
        else:
            return Response(serializer.errors)
        #params = request.DATA
        #for key in params.keys():
        #    #Convert boolean strings to python bool
        #    if not hasattr(profile, key):
        #        try:
        #            return Response(400, content="Cannot assign property %s" % key)
        #        except:
        #            logger.exception("Problem with service.api.profile for key.")
        #    if params[key] in ['f','false','False']:
        #        val = False
        #    elif params[key] in ['t','true','True']:
        #        val = True
        #    else:
        #        val = params[key]
        #    setattr(profile, key, val)
        #try:
        #    profile.full_clean()
        #    profile.save()
        #except ValidationError, val:
        #    return Response(400, content=val)
        #except:
        #    logger.exception("Problem with service.api.profile.put.")
        #serialized_data = ProfileSerializer(user.get_profile()).data

