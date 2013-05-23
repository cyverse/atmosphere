"""
Atmosphere service instance rest api.
"""
from datetime import datetime
import time
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.reverse import reverse

from threepio import logger

from authentication.decorators import api_auth_token_required

from core.models import Provider, Identity

class APIRoot(APIView):

    @api_auth_token_required
    def get(self, request):
        """
        Returns all available URLs based on the user profile
        """
        user = request.user
        profile = user.get_profile() 
        identity_id = profile.selected_identity.id
        provider_id = profile.selected_identity.provider.id
        data = {
                'provider':reverse('provider-list',
                    request=request),
                'identity':reverse('identity-list',
                    args=(provider_id,), request=request),
                'volume':reverse('volume-list',
                    args=(provider_id, identity_id), request=request),
                'meta':reverse('meta-detail',
                    args=(provider_id, identity_id), request=request),
                'instance':reverse('instance-list',
                    args=(provider_id, identity_id), request=request),
                'machine':reverse('machine-list',
                    args=(provider_id, identity_id), request=request),
                'size':reverse('size-list',
                    args=(provider_id, identity_id), request=request),
                'profile':reverse('profile', request=request)
               }
        return Response(data)

