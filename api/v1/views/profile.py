"""
Atmosphere service instance rest api.

"""
from rest_framework.response import Response
from rest_framework import status

from django.utils import timezone
from core.exceptions import InvalidUser
from api.v1.views.base import AuthAPIView
from api.v1.serializers import ProfileSerializer, AtmoUserSerializer


class Profile(AuthAPIView):

    """
    Profile can be thought of as the 'entry-point' to the Atmosphere APIs.
    Once authentiated, a user can find their default provider and identity.
    The IDs for provider and Identity can be used to navigate the rest of
    the API.
    """

    def get(self, request, provider_uuid=None, identity_uuid=None):
        """
        Authentication Required, retrieve the users profile.
        """
        user = request.user
        # THIS IS A HACK! -- This check covered by permissions in v2
        if not user.is_enabled:
            return Response(
                "The account <%s> has been disabled by an Administrator. "
                "Please contact your Cloud Administrator for more information."
                % (user.username,), status=403)  # Forbidden

        profile = user.userprofile
        try:
            serialized_data = ProfileSerializer(profile).data
        except InvalidUser as exc:
            return Response(exc.message,
                            status=status.HTTP_403_FORBIDDEN)
        user.select_identity()
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
        mutable_data = request.data.copy()
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
        serializer = ProfileSerializer(profile, data=request.data)
        if serializer.is_valid():
            serializer.save()
            response = Response(serializer.data)
            return response
        else:
            return Response(serializer.errors)
