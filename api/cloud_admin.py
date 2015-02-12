from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

from api.permissions import ApiAuthRequired, CloudAdminRequired
from api.serializers import CloudAdminSerializer,\
    CloudAdminActionListSerializer, MachineRequestSerializer,\
    IdentitySerializer, AccountSerializer
from core.models.machine_request import MachineRequest as CoreMachineRequest
from core.models.cloud_admin import CloudAdministrator
from core.models.identity import Identity as CoreIdentity
from core.models.group import IdentityMembership
from service.driver import get_account_driver

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

    permission_classes = (CloudAdminRequired,)

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

    permission_classes = (CloudAdminRequired,)

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
        serializer = CloudAdminActionListSerializer(
            admin, context={'request': request})
        return Response(serializer.data)


#class CloudAdminUserList(APIView):



class CloudAdminImagingRequestList(APIView):
    """
    Cloud Administration API for handling Imaging Requests
    """

    permission_classes = (CloudAdminRequired,)

    def get(self, request, cloud_admin_uuid):
        """
        """
        user = request.user
        admin = _get_administrator_account(user, cloud_admin_uuid)
        machine_reqs = CoreMachineRequest.objects.filter(
            instance__source__provider=admin.provider)
        serializer = MachineRequestSerializer(machine_reqs, many=True)
        return Response(serializer.data)


class CloudAdminImagingRequest(APIView):
    """
    This is the staff portal for machine requests
    A staff member can view any machine request by its ID
    """

    permission_classes = (CloudAdminRequired,)

    def get(self, request,
            cloud_admin_uuid, machine_request_id, action=None):
        """
        OPT 1 for approval: via GET with /approve or /deny
        This is a convenient way to approve requests remotely
        """

        admin = _get_administrator_account(request.user, cloud_admin_uuid)
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
        try:
            machine_request = CoreMachineRequest.objects.get(
                instance__source__provider=admin.provider,
                id=machine_request_id)
        except CoreMachineRequest.DoesNotExist:
            return Response('No machine request with id %s'
                            % machine_request_id,
                            status=status.HTTP_404_NOT_FOUND)

        data = request.DATA
        # Behavior will remove 'status' if its being updated.
        # Status should only be updated if denied or skipped.
        # Status of 'approve','continue' will use the machine_request.status
        # to allow restarting the request at the correct point in time.
        start_request = False
        if 'status' in data:
            _status = data['status'].lower()
            if machine_request.status == 'completed':
                return Response(
                    "Cannot update status of 'completed' request",
                    status=status.HTTP_409_conflict)
            elif _status in ['approve', 'continue']:
                data.pop('status')
                start_request = True
            elif _status not in ['deny', 'skip']:
                return Response(
                    "Bad Status Value: %s. "
                    "Available choices for a status update are: "
                    "approve, continue, deny, skip")
                
        serializer = MachineRequestSerializer(
            machine_request, data=data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors,
                            status=status.HTTP_400_BAD_REQUEST)
        # Only run task if status is 'approve'
        machine_request = serializer.save()
        mr_data = serializer.data
        if start_request:
            start_machine_imaging(machine_request)
        return Response(mr_data, status=status.HTTP_200_OK)


class CloudAdminAccountList(APIView):
    """
    This API is used to provide account management.
    provider_uuid -- The id of the provider whose account you want to manage.
    """
    permission_classes = (CloudAdminRequired,)

    def get(self, request, cloud_admin_uuid):
        """
        Return a list of ALL users found on provider_uuid
        """
        user = request.user
        admin = _get_administrator_account(user, cloud_admin_uuid)
        # Query for identities, used to retrieve memberships.
        identity_list = admin.provider.identity_set.all()
        memberships = IdentityMembership.objects.filter(
            identity__in=identity_list)
        serializer = AccountSerializer(memberships, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, cloud_admin_uuid):
        """
        Passes in:
        Username (To apply the identity to)
        Credentials (Nested, will be applied to new identity)

        """
        user = request.user
        data = request.DATA

        admin = _get_administrator_account(user, cloud_admin_uuid)
        driver = get_account_driver(admin.provider.uuid)
        missing_args = driver.clean_credentials(data)
        if missing_args:
            raise Exception("Cannot create account. Missing credentials: %s"
                            % missing_args)
        identity = driver.create_account(**data)
        # Account serializer instead?
        serializer = IdentityDetailSerializer(identity)
        if serializer.is_valid():
            # NEVER FAILS
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # driver = get_account_driver(provider_uuid)
        # #TODO: Maybe get_or_create identity on list_users?
        # users = driver.list_users()
        # #Maybe identities?
        # serialized_data = AccountSerializer(users).data
        # response = Response(serialized_data)
        # return response


class CloudAdminAccountEnable(APIView):
    """
    This API is used to Enable/Disable a specific identity on your Cloud Provider.
    """
    permission_classes = (CloudAdminRequired,)

    def get(self, request, cloud_admin_uuid, username):
        """
        Detailed view of all identities for provider,user combination.
        username -- The username to match identities
        """
        #identities = CoreIdentity.objects.filter(provider__uuid=provider_uuid,
        #                                         created_by__username=username)
        #serialized_data = IdentitySerializer(identities, many=True).data
        #return Response(serialized_data)
        pass
