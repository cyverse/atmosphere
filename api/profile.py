"""
Atmosphere service instance rest api.

"""
## Frameworks
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.reverse import reverse

from threepio import logger
## Atmosphere Libraries


from api.permissions import InMaintenance, ApiAuthRequired
from api.serializers import ProfileSerializer, AtmoUserSerializer
from core.models.profile import UserProfile

class Profile(APIView):
    """Profile can be thought of as the 'entry-point' to the Atmosphere APIs.
    Once authentiated, a user can find their default provider and identity.
    The IDs for provider and Identity can be used to navigate the rest of
    the API.
    """

    permission_classes = (ApiAuthRequired,)

    def get(self, request, provider_uuid=None, identity_uuid=None):
        """Authentication Required, retrieve the users profile."""
        #logger.info(request.user)
        user = request.user
        #logger.debug(user.userprofile)
        profile = user.userprofile
        serialized_data = ProfileSerializer(profile).data
        identity = user.select_identity()
        identity_uuid = identity.id
        provider_uuid = identity.provider.id
        response = Response(serialized_data)
        return response

    def patch(self, request, provider_uuid=None, identity_uuid=None):
        """
        Authentication Required, Update the users profile.
        Returns: 203 - Success, no body.
        400 - Bad key/value on update, errors in body.
        """
        user = request.user
        profile = user.userprofile
        mutable_data = request.DATA.copy()
        if "selected_identity" in mutable_data:
            user_data = {"selected_identity":
                         mutable_data.pop("selected_identity")}
            serializer = AtmoUserSerializer(user,
                                            data=user_data,
                                            partial=True)
            if serializer.is_valid():
                serializer.save()
        serializer = ProfileSerializer(profile,
                                       data=mutable_data,
                                       partial=True)
        if serializer.is_valid():
            serializer.save()
            response = Response(serializer.data)
            return response
        else:
            return Response(serializer.errors)

    def put(self, request, provider_uuid=None, identity_uuid=None):
        """
        Authentication Required, Update the users profile.
        Returns: 203 - Success, no body.
        400 - Bad key/value on update, errors in body.
        """
        user = request.user
        profile = user.userprofile
        serializer = ProfileSerializer(profile, data=request.DATA)
        if serializer.is_valid():
            serializer.save()
            response = Response(serializer.data)
            return response
        else:
            return Response(serializer.errors)
