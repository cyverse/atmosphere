from django.contrib.auth import authenticate, login
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from api.permissions import ApiAuthOptional
from atmosphere.settings import secrets
from authentication import createAuthToken

class Authentication(APIView):
    #permission_classes = (ApiAuthOptional,)

    def get(self, request):
        if not request.user:
            return Response("Logged-in User or POST required to retrieve AuthToken",
                    status=status.HTTP_403_FORBIDDEN)
        return self._token_for_username(request.user.username)

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
