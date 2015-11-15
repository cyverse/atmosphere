"""
Atmosphere service export request rest api.

"""
import copy

from rest_framework.response import Response
from rest_framework import status

from threepio import logger

from chromogenic.tasks import instance_export_task

from core.models.export_request import ExportRequest as CoreExportRequest

from api.v1.serializers import ExportRequestSerializer
from api.v1.views.base import AuthAPIView


class ExportRequestList(AuthAPIView):

    """
    Starts the process of bundling a running instance
    """

    def get(self, request, provider_uuid, identity_uuid):
        """
        """
        all_user_reqs = CoreExportRequest.objects.filter(
            export_owner=request.user)
        serialized_data = ExportRequestSerializer(all_user_reqs).data
        response = Response(serialized_data)
        return response

    def post(self, request, provider_uuid, identity_uuid):
        """
        Create a new object based on DATA
        Start the ExportRequestThread if not running
            & Add all images marked 'queued'
        OR
        Add self to ExportRequestQueue
        Return to user with "queued"
        """
        # request.data is r/o
        data = copy.deepcopy(request.data)
        owner = request.user.username
        # Staff members can export on users behalf..
        if data.get('created_for') and request.user.is_staff:
            owner = data.get('created_for')
        data['owner'] = owner
        logger.info(data)
        serializer = ExportRequestSerializer(data=data)
        if serializer.is_valid():
            export_request = serializer.save()
            instance_export_task.delay(export_request)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ExportRequest(AuthAPIView):

    """
    Represents:
        Calls to modify the single exportrequest
    """

    def get(self, request, provider_uuid, identity_uuid, export_request_id):
        """
        """
        try:
            export_request = CoreExportRequest.objects.get(
                id=export_request_id)
        except CoreExportRequest.DoesNotExist:
            return Response(
                "No machine request with id %s" % export_request_id,
                status=status.HTTP_404_NOT_FOUND)
        serialized_data = ExportRequestSerializer(export_request).data
        response = Response(serialized_data)
        return response

    def patch(self, request, provider_uuid, identity_uuid, export_request_id):
        data = request.data
        try:
            export_request = CoreExportRequest.objects.get(
                id=export_request_id)
        except CoreExportRequest.DoesNotExist:
            return Response(
                "No export request with id %s" % export_request_id,
                status=status.HTTP_404_NOT_FOUND)
        serializer = ExportRequestSerializer(export_request,
                                             data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, provider_uuid, identity_uuid, export_request_id):
        data = request.data
        try:
            export_request = CoreExportRequest.objects.get(
                id=export_request_id)
        except CoreExportRequest.DoesNotExist:
            return Response(
                'No export request with id %s' % export_request_id,
                status=status.HTTP_404_NOT_FOUND)

        serializer = ExportRequestSerializer(export_request,
                                             data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
