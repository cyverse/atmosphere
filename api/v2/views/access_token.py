from rest_framework import status
from rest_framework.response import Response

from core.models import AccessToken, AtmosphereUser
from core.models.access_token import create_access_token

from api.exceptions import invalid_auth
from api.v2.serializers.details import AccessTokenSerializer
from api.v2.views.base import AuthModelViewSet

class AccessTokenViewSet(AuthModelViewSet):

    """
    API endpoint that allows AccessTokens to be viewed or edited.
    """
    serializer_class = AccessTokenSerializer

    def get_queryset(self):
        """
        Filter projects by current user.
        """
        return AccessToken.objects.filter(token__user=self.request.user)

    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        name = request.data.get('name', None)
        user = request.user
        access_token = create_access_token(user, name, issuer="Personal-Access-Token")

        json_response = {
            'token': access_token.token_id,
            'id': access_token.id,
            'name': name,
            'issued_time': access_token.token.issuedTime
        }
        return Response(json_response, status=status.HTTP_201_CREATED)
