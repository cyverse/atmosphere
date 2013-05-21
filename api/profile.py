"""
Atmosphere service instance rest api.

"""
## Frameworks
from rest_framework.views import APIView
from rest_framework.response import Response

from threepio import logger
## Atmosphere Libraries

from authentication.decorators import api_auth_token_required

from api.serializers import ProfileSerializer


class Profile(APIView):
    """
    """

    @api_auth_token_required
    def get(self, request, provider_id=None, identity_id=None):
        """
        """
        #logger.info(request.user)
        user = request.user
        #logger.debug(user.get_profile())
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
        user = request.user
        profile = user.get_profile()
        serializer = ProfileSerializer(profile,
                                       data=request.DATA, partial=True)
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
        user = request.user
        profile = user.get_profile()
        serializer = ProfileSerializer(profile, data=request.DATA)
        if serializer.is_valid():
            serializer.save()
            response = Response(serializer.data)
            return response
        else:
            return Response(serializer.errors)
