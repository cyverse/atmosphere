from django.contrib.auth import authenticate, login

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from atmosphere.settings import secrets
from django_cyverse_auth.models import create_token, lookupSessionToken

from api.permissions import ApiAuthIgnore
from api.exceptions import invalid_auth
from api.v1.serializers import TokenSerializer


class Authentication(APIView):

    permission_classes = (ApiAuthIgnore,)

    def get(self, request):
        user = request.user
        if not user.is_authenticated():
            return Response("Logged-in User or POST required "
                            "to retrieve AuthToken",
                            status=status.HTTP_403_FORBIDDEN)
        token = lookupSessionToken(request)
        if not token:
            token = create_token(user.username, request.session.pop('token_key',None))
        serialized_data = TokenSerializer(token).data
        return Response(serialized_data, status=status.HTTP_200_OK)

    def post(self, request):
        data = request.data
        username = data.get('username', None)
        password = data.get('password', None)
        project_name = data.get('project_name', None)
        auth_url = data.get('auth_url', None)
        if not username:
            return invalid_auth("Username missing")

        auth_kwargs = {"username":username, "password":password, "request":request}
        if project_name and auth_url:
            auth_kwargs['project_name'] = project_name
            auth_kwargs['auth_url'] = auth_url
        user = authenticate(**auth_kwargs)
        if not user:
            return invalid_auth("Username/Password combination was invalid")

        login(request, user)
        issuer_backend = request.session.get('_auth_user_backend', '').split('.')[-1]
        return self._create_token(
            request, user.username, request.session.pop('token_key', None),
            issuer=issuer_backend)

    def _create_token(self, request, username, token_key, issuer="DRF"):
        token = create_token(username, token_key, issuer=issuer)
        expireTime = token.issuedTime + secrets.TOKEN_EXPIRY_TIME
        auth_json = {
            'token': token.key,
            'username': token.user.username,
            'expires': expireTime.strftime("%b %d, %Y %H:%M:%S")
        }
        request.session['token'] = token.key
        return Response(auth_json, status=status.HTTP_201_CREATED)
