from django.core.paginator import Paginator,\
    PageNotAnInteger, EmptyPage

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from threepio import logger

from core.models.application import ApplicationBookmark, Application
from authentication.decorators import api_auth_token_required
from api import failure_response
from api.permissions import InMaintenance
from api.serializers import ApplicationBookmarkSerializer


class ApplicationBookmarkList(APIView):
    """
    Represents:
        A Manager of Machine
        Calls to the Machine Class
    TODO: POST when we have programmatic image creation/snapshots
    """

    permission_classes = (InMaintenance,)

    @api_auth_token_required
    def get(self, request, **kwargs):
        """
        Using provider and identity, getlist of machines
        TODO: Cache this request
        """
        user = request.user
        app_bookmarks = ApplicationBookmark.objects.filter(user=user)
        serialized_data = ApplicationBookmarkSerializer(app_bookmarks,
                                                        many=True).data
        response = Response(serialized_data)
        return response


class ApplicationBookmarkDetail(APIView):
    """
    Represents:
        A Manager of Machine
        Calls to the Machine Class
    TODO: POST when we have programmatic image creation/snapshots
    """

    permission_classes = (InMaintenance,)

    @api_auth_token_required
    def get(self, request, app_uuid, **kwargs):
        user = request.user
        app_bookmark = ApplicationBookmark.objects.filter(
                application__uuid=app_uuid,
                user=user)
        if not app_bookmark:
            return failure_response(status.HTTP_404_NOT_FOUND,
                                    "Application with uuid %s does not exist "
                                    "OR has not been bookmarked" % app_uuid)
        app_bookmark = app_bookmark[0]
        serialized_data = ApplicationBookmarkSerializer(app_bookmark).data
        response = Response(serialized_data)
        return response

    @api_auth_token_required
    def put(self, request, app_uuid, **kwargs):
        """
        TODO: Determine who is allowed to edit machines besides
            core_machine.owner
        """
        user = request.user
        data = request.DATA
        app = Application.objects.filter(uuid=app_uuid)
        if not app:
            return failure_response(status.HTTP_404_NOT_FOUND,
                                    "No Application with uuid %s" % app_uuid)
        app = app[0]
        if 'marked' in data:
            app_bookmark, _ = ApplicationBookmark.objects.get_or_create(
                application=app,
                user=user)
            serialized_data = ApplicationBookmarkSerializer(app_bookmark).data
            response = Response(serialized_data)
            return response
        return failure_response(status.HTTP_400_BAD_REQUEST,
                "Missing 'marked' in PUT data")
