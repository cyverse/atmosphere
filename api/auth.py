from django.contrib.auth import authenticate, login
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from api.permissions import ApiAuthIgnore
from atmosphere.settings import secrets
from authentication import createAuthToken, lookupSessionToken
from api.serializers import TokenSerializer

class Authentication(APIView):
    permission_classes = (ApiAuthIgnore,)

    def get(self, request):
        user = request.user
        if not user.is_authenticated():
            return Response("Logged-in User or POST required to retrieve AuthToken",
                    status=status.HTTP_403_FORBIDDEN)
        # Authenticated users have tokens
        token = lookupSessionToken(request)
        if token.is_expired():
            # Sanity Check: New tokens should be created
            # when auth token is expired.
            token = createAuthToken(user.username)
        serialized_data = TokenSerializer(token).data
        return Response(serialized_data, status=status.HTTP_200_OK)

    def post(self, request):
        data = request.DATA
        username = data.get('username', None)
        password = data.get('password', None)
        if not username:
            raise Exception("Where my username")
        user = authenticate(username=username, password=password,
                    request=request)
        login(request, user)
        return self._token_for_username(user.username)

    def _token_for_username(self, username):
        token = createAuthToken(username)
        expireTime = token.issuedTime + secrets.TOKEN_EXPIRY_TIME
        auth_json = {
            'token': token.key,
            'username': token.user.username,
            'expires': expireTime.strftime("%b %d, %Y %H:%M:%S")
        }
        return Response(auth_json, status=status.HTTP_201_CREATED)
