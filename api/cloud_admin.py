from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

from api.permissions import ApiAuthRequired
from api.serializers import CloudAdminSerializer,\
    CloudAdminActionListSerializer, MachineRequestSerializer
from core.models.machine_request import MachineRequest as CoreMachineRequest
from core.models.cloud_admin import CloudAdministrator

from service.tasks.machine import start_machine_imaging


def _get_administrator_accounts(user):
    return CloudAdministrator.objects.filter(user=user)


def _get_administrator_account(user, admin_uuid):
    try:
        return CloudAdministrator.objects.get(uuid=admin_uuid, user=user)
    except CloudAdministrator.DoesNotExist:
        return None


class CloudAdmin(APIView):
    """
    Cloud Administration API
    """

    permission_classes = (ApiAuthRequired,)

    def get(self, request):
        """
        """
        user = request.user
        admins = _get_administrator_accounts(user)
        serializer = CloudAdminSerializer(admins, many=True)
        return Response(serializer.data)


class CloudAdminActionsList(APIView):
    """
    Cloud Administration API
    """

    permission_classes = (ApiAuthRequired,)

    def get(self, request, cloud_admin_uuid):
        """
        """
        user = request.user
        admin = _get_administrator_account(user, cloud_admin_uuid)
        if not admin:
            return Response(
                "Cloud Administrator with UUID=%s is not "
                "accessible to user:%s"
                % (cloud_admin_uuid, user.username),
                status=status.HTTP_400_BAD_REQUEST)
        serializer = CloudAdminActionListSerializer(admin, many=True)
        return Response(serializer.data)


class CloudAdminImagingRequestList(APIView):
    """
    Cloud Administration API for handling Imaging Requests
    """

    permission_classes = (ApiAuthRequired,)

    def get(self, request, cloud_admin_uuid):
        """
        """
        user = request.user
        admin = _get_administrator_account(user, cloud_admin_uuid)
        if not admin:
            return Response(
                "Cloud Administrator with UUID=%s is not "
                "accessible to user:%s"
                % (cloud_admin_uuid, user.username),
                status=status.HTTP_400_BAD_REQUEST)
        machine_reqs = CoreMachineRequest.objects.filter(
            instance__source__provider=admin.provider)
        serializer = MachineRequestSerializer(machine_reqs, many=True)
        return Response(serializer.data)


class CloudAdminImagingRequest(APIView):
    """
    This is the staff portal for machine requests
    A staff member can view any machine request by its ID
    """

    permission_classes = (ApiAuthRequired,)

    def get(self, request,
            cloud_admin_uuid, machine_request_id, action=None):
        """
        OPT 1 for approval: via GET with /approve or /deny
        This is a convenient way to approve requests remotely
        """

        admin = _get_administrator_account(request.user, cloud_admin_uuid)
        if not admin:
            return Response(
                "Cloud Administrator with UUID=%s is not "
                "accessible to user:%s"
                % (cloud_admin_uuid, request.user.username),
                status=status.HTTP_400_BAD_REQUEST)
        try:
            machine_request = CoreMachineRequest.objects.get(
                instance__source__provider=admin.provider,
                id=machine_request_id)
        except CoreMachineRequest.DoesNotExist:
            return Response('No machine request with id %s'
                            % machine_request_id,
                            status=status.HTTP_404_NOT_FOUND)

        if not action:
            serializer = MachineRequestSerializer(machine_request)
            return Response(serializer.data, status=status.HTTP_200_OK)

        # Don't update the request unless its pending or error
        # Otherwise use the existing status to 'start machine imaging'
        if machine_request.status in ['error', 'pending']:
            machine_request.status = action
            machine_request.save()

        # Only run task if status is 'approve'
        if machine_request.status == 'approve':
            start_machine_imaging(machine_request)

        serializer = MachineRequestSerializer(machine_request)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request,
              cloud_admin_uuid, machine_request_id, action=None):
        """
        OPT2 for approval: sending a PATCH to the machine request with
          {"status":"approve/deny"}
        
        Modfiy attributes on a machine request
        """
        admin = _get_administrator_account(request.user, cloud_admin_uuid)
        if not admin:
            return Response(
                "Cloud Administrator with UUID=%s is not "
                "accessible to user:%s"
                % (cloud_admin_uuid, request.user.username),
                status=status.HTTP_400_BAD_REQUEST)

        try:
            machine_request = CoreMachineRequest.objects.get(
                instance__source__provider=admin.provider,
                id=machine_request_id)
        except CoreMachineRequest.DoesNotExist:
            return Response('No machine request with id %s'
                            % machine_request_id,
                            status=status.HTTP_404_NOT_FOUND)

        data = request.DATA
        # Do NOT overwrite the status if its in a Non-Error, Non-Pending state
        # It will allow us to 'start from where we left off'
        if 'status' in data \
                and machine_request.status not in ['error', 'pending']:
            passed_status = data['status']
            data['status'] = machine_request.status

        serializer = MachineRequestSerializer(
            machine_request, data=data, partial=True)
        if serializer.is_valid():
            # Only run task if status is 'approve'
            if passed_status == 'approve':
                start_machine_imaging(machine_request)
            serializer.save()
        # Object may have changed
        serializer = MachineRequestSerializer(machine_request)
        return Response(serializer.data, status=status.HTTP_200_OK)
