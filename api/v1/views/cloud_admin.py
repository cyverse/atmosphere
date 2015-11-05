from functools import wraps

from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

from core.models.machine_request import MachineRequest as CoreMachineRequest
from core.models.cloud_admin import CloudAdministrator
from core.models.provider import Provider, ProviderInstanceAction
from core.models.group import IdentityMembership

from service.driver import get_account_driver
from service.tasks.machine import start_machine_imaging

from api.permissions import ApiAuthRequired, CloudAdminRequired,\
    InMaintenance
from api.v1.serializers import MachineRequestSerializer,\
    IdentitySerializer, AccountSerializer,\
    PATCH_ProviderInstanceActionSerializer,\
    POST_ProviderInstanceActionSerializer,\
    ProviderInstanceActionSerializer


def _get_administrator_accounts(user):
    return CloudAdministrator.objects.filter(user=user)


def _get_administrator_account(user, admin_uuid):
    try:
        return CloudAdministrator.objects.get(uuid=admin_uuid, user=user)
    except CloudAdministrator.DoesNotExist:
        return None


class CloudAdminImagingRequestList(APIView):

    """
    Cloud Administration API for handling Imaging Requests
    """

    permission_classes = (ApiAuthRequired,
                          InMaintenance,
                          CloudAdminRequired,)

    def get(self, request):
        user = request.user
        machine_reqs = CoreMachineRequest.objects.filter(
            instance__source__provider__cloudadministrator__user=user
        ).order_by('-start_date')
        serializer = MachineRequestSerializer(machine_reqs, many=True)
        return Response(serializer.data)


class CloudAdminImagingRequest(APIView):

    """
    This is the staff portal for machine requests
    A staff member can view any machine request by its ID
    """

    permission_classes = (ApiAuthRequired,
                          InMaintenance,
                          CloudAdminRequired,)

    def get(self, request,
            machine_request_id, action=None):
        """
        OPT 1 for approval: via GET with /approve or /deny
        This is a convenient way to approve requests remotely
        """

        user = request.user
        try:
            machine_request = CoreMachineRequest.objects.get(
                instance__source__provider__cloudadministrator__user=user,
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
        if machine_request.old_status in ['error', 'pending']:
            machine_request.old_status = action
            machine_request.save()

        # Only run task if status is 'approve'
        if machine_request.old_status == 'approve':
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
        user = request.user
        try:
            machine_request = CoreMachineRequest.objects.get(
                instance__source__provider__cloudadministrator__user=user,
                id=machine_request_id)
        except CoreMachineRequest.DoesNotExist:
            return Response('No machine request with id %s'
                            % machine_request_id,
                            status=status.HTTP_404_NOT_FOUND)

        data = request.data
        # Behavior will remove 'status' if its being updated.
        # Status should only be updated if denied or skipped.
        # Status of 'approve','continue' will use the machine_request.status
        # to allow restarting the request at the correct point in time.
        start_request = False
        if 'status' in data:
            _status = data['status'].lower()
            if machine_request.old_status == 'completed':
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
    permission_classes = (ApiAuthRequired,
                          InMaintenance,
                          CloudAdminRequired,)

    def get(self, request):
        """
        Return a list of ALL IdentityMemberships found on provider_uuid
        """
        user = request.user
        memberships = IdentityMembership.objects.filter(
            identity__provider__cloudadministrator__user=user
        ).order_by('member__name')
        serializer = AccountSerializer(memberships, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, cloud_admin_uuid):
        """
        Passes in:
        Username (To apply the identity to)
        Credentials (Nested, will be applied to new identity)

        """
        user = request.user
        data = request.data
        try:
            provider_uuid = data['provider']
            provider = Provider.objects.get(
                cloudadministrator__user=user,
                uuid=provider_uuid)
        except KeyError:
            return Response(
                "Missing 'provider' key, Expected UUID. Received no value.",
                status=status.HTTP_409_conflict)
        except Exception:
            return Response(
                "Provider with UUID %s does not exist" % provider_uuid,
                status=status.HTTP_409_conflict)
            raise Exception
        driver = get_account_driver(provider)
        missing_args = driver.clean_credentials(data)
        if missing_args:
            raise Exception("Cannot create account. Missing credentials: %s"
                            % missing_args)
        identity = driver.create_account(**data)
        serializer = IdentitySerializer(identity)

        # TODO: Account creation SHOULD return IdentityMembership NOT identity.
        return Response(serializer.data)


class CloudAdminAccount(APIView):

    """
    This API is used to Enable/Disable a specific identity on
    your Cloud Provider.
    """

    permission_classes = (ApiAuthRequired,
                          InMaintenance,
                          CloudAdminRequired,)

    def get(self, request, username):
        """
        Detailed view of all identities for provider,user combination.
        username -- The username to match identities
        """
        user = request.user
        memberships = IdentityMembership.objects.filter(
            identity__provider__cloudadministrator__user=user,
            identity__created_by__username=username).order_by('member__name')
        serializer = AccountSerializer(memberships, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CloudAdminInstanceActionList(APIView):

    """
    This API is used to provide account management.
    provider_uuid -- The id of the provider whose account you want to manage.
    """

    def get(self, request):
        """
        Return a list of ALL users found on provider_uuid
        """
        p_instance_actions = ProviderInstanceAction.objects.filter(
            provider__cloudadministrator__user=request.user,
        )
        serializer = ProviderInstanceActionSerializer(
            p_instance_actions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        """
        Create a new "ProviderInstanceAction"
        """
        data = request.data
        serializer = POST_ProviderInstanceActionSerializer(data=data)
        if serializer.is_valid():
            new_action = serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CloudAdminInstanceAction(APIView):

    """
    This API is used to provide account management.
    provider_uuid -- The id of the provider whose account you want to manage.
    """

    permission_classes = (ApiAuthRequired,
                          InMaintenance,
                          CloudAdminRequired,)

    def get(self, request, provider_instance_action_id):
        """
        Return a list of ALL users found on provider_uuid
        """
        try:
            p_instance_action = ProviderInstanceAction.objects.get(
                id=provider_instance_action_id)
        except ProviderInstanceAction.DoesNotExist:
            return Response("Bad ID", status=status.HTTP_400_BAD_REQUEST)
        serializer = ProviderInstanceActionSerializer(p_instance_action)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, provider_instance_action_id):
        """
        Return a list of ALL users found on provider_uuid
        """
        data = request.data
        try:
            p_instance_action = ProviderInstanceAction.objects.get(
                id=provider_instance_action_id)
        except ProviderInstanceAction.DoesNotExist:
            return Response("Bad ID", status=status.HTTP_400_BAD_REQUEST)
        serializer = PATCH_ProviderInstanceActionSerializer(
            p_instance_action, data=data, partial=True)
        if serializer.is_valid():
            p_instance_action = serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
