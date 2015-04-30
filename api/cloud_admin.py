from functools import wraps

from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

from api.permissions import CloudAdminRequired
from api.serializers import MachineRequestSerializer,\
    IdentitySerializer, AccountSerializer, \
    PATCH_ProviderInstanceActionSerializer, \
    POST_ProviderInstanceActionSerializer, \
    ProviderInstanceActionSerializer, ResolveQuotaRequestSerializer, \
    ResolveAllocationRequestSerializer
from core.models.machine_request import MachineRequest as CoreMachineRequest
from core.models.cloud_admin import CloudAdministrator
from core.models.provider import Provider, ProviderInstanceAction
from core.models.group import IdentityMembership

from core.models.request import AllocationRequest, QuotaRequest

from service.driver import get_account_driver

from service.tasks.machine import start_machine_imaging


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

    permission_classes = (CloudAdminRequired,)

    def get(self, request):
        """
        """
        user = request.user
        machine_reqs = CoreMachineRequest.objects.filter(
            instance__source__provider__cloudadministrator__user=user).order_by('-start_date')
        serializer = MachineRequestSerializer(machine_reqs, many=True)
        return Response(serializer.data)


class CloudAdminImagingRequest(APIView):
    """
    This is the staff portal for machine requests
    A staff member can view any machine request by its ID
    """

    permission_classes = (CloudAdminRequired,)

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
        user = request.user
        try:
            machine_request = CoreMachineRequest.objects.get(
                instance__source__provider__cloudadministrator__user=user,
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

    def get(self, request):
        """
        Return a list of ALL IdentityMemberships found on provider_uuid
        """
        user = request.user
        memberships = IdentityMembership.objects.filter(
            identity__provider__cloudadministrator__user=user).order_by('member__name')
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
        # membership = driver.create_account(**data)
        # serializer = AccountSerializer(membership)
        return Response(serializer.data)


class CloudAdminRequestListMixin(object):
    permission_classes = (CloudAdminRequired,)

    model = None
    serializer_class = None

    def get_objects(self, unresolved=False):
        """
        Return a list of requests

        unresolved - when True only return unresolved requests
        """
        if unresolved:
            return self.model.get_unresolved()
        return self.model.objects.all()

    def get(self, request):
        """
        Return a list of A
        """
        objects = self.get_objects()
        data = self.serializer_class(objects, many=True).data
        return Response(data)


class CloudAdminRequestDetailMixin(object):
    """
    Detail Mixin to manage a request
    """
    permission_classes = (CloudAdminRequired,)
    identifier_key = "uuid"

    model = None
    serializer_class = None

    def approve(self, request):
        """
        Perform the approved action for the request
        """

    def deny(self, request):
        """
        Perform the denied action for the request
        """

    def get_object(self, identifier):
        """
        Fetch the request object
        """
        kwargs = {self.identifier_key: identifier}
        return get_object_or_404(self.model, **kwargs)

    def _unresolved_requests_only(fn):
        """
        Only allow a unresolved request to be processed
        """
        @wraps(fn)
        def wrapper(self, request, identifier):
            pending_request = self.get_object(identifier)
            if pending_request.is_closed():
                message = "This request has already been resolved."
                return Response(data={"message": message},
                                status=status.HTTP_405_METHOD_NOT_ALLOWED)
            else:
                return fn(self, request, identifier)
        return wrapper

    def _perform_update(self, request):
        """
        Action to be performed to a closed request
        """
        if request.is_approved():
            self.approve(request)

        if request.is_denied():
            self.deny(request)

    def get(self, request, identifier):
        """
        Return the request for the specific identifier
        """
        pending_request = self.get_object(identifier)
        data = self.serializer_class(pending_request).data
        return Response(data)

    @_unresolved_requests_only
    def put(self, request, identifier):
        """
        Update the request for the specific identifier
        """
        pending_request = self.get_object(identifier)
        request.data["end_date"] = timezone.now()

        serializer = self.serializer_class(pending_request, request.data)
        if not serializer.is_valid():
            return Response(data=serializer.errors,
                            status=status.HTTP_400_BAD_REQUEST)

        pending_request = serializer.save()
        self._perform_update(pending_request)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @_unresolved_requests_only
    def patch(self, request, identifier):
        """
        Partially update the request for the specific identifier
        """
        request.data["end_date"] = timezone.now()
        pending_request = self.get_object(identifier)
        serializer = self.serializer_class(pending_request, request.data,
                                           partial=True)

        if not serializer.is_valid():
            return Response(serializer.errors,
                            status=status.HTTP_400_BAD_REQUEST)

        pending_request = serializer.save()
        self._perform_update(pending_request)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CloudAdminQuotaList(APIView, CloudAdminRequestListMixin):
    model = QuotaRequest
    serializer_class = ResolveQuotaRequestSerializer


class CloudAdminQuotaRequest(APIView, CloudAdminRequestDetailMixin):
    """
    Manage user quota requests
    """
    model = QuotaRequest
    serializer_class = ResolveQuotaRequestSerializer

    def approve(self, pending_request):
        """
        Updates the quota for the request
        """
        membership = pending_request.membership
        membership.quota = pending_request.quota
        membership.approve_quota(pending_request.id)


class CloudAdminAllocationList(APIView, CloudAdminRequestListMixin):
    model = AllocationRequest
    serializer_class = ResolveAllocationRequestSerializer


class CloudAdminAllocationRequest(APIView, CloudAdminRequestDetailMixin):
    """
    Manage user allocation requests
    """
    model = AllocationRequest
    serializer_class = ResolveAllocationRequestSerializer

    def approve(self, pending_request):
        """
        Updates the allocation for the request
        """
        membership = pending_request.membership
        membership.allocation = pending_request.allocation
        membership.save()


class CloudAdminAccount(APIView):
    """
    This API is used to Enable/Disable a specific identity on your Cloud Provider.
    """
    permission_classes = (CloudAdminRequired,)

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
    permission_classes = (CloudAdminRequired,)
    def get(self, request):
        """
        Return a list of ALL users found on provider_uuid
        """
        p_instance_actions = ProviderInstanceAction.objects.filter(
            provider__cloudadministrator__user=request.user,
        )
        serializer = ProviderInstanceActionSerializer(p_instance_actions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    def post(self, request):
        """
        Create a new "ProviderInstanceAction"
        """
        data = request.DATA
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
    permission_classes = (CloudAdminRequired,)
    def get(self, request, provider_instance_action_id):
        """
        Return a list of ALL users found on provider_uuid
        """
        try:
           p_instance_action = ProviderInstanceAction.objects.get(id=provider_instance_action_id)
        except ProviderInstanceAction.DoesNotExist:
            return Response("Bad ID", status=status.HTTP_400_BAD_REQUEST)
        serializer = ProviderInstanceActionSerializer(p_instance_action)
        return Response(serializer.data, status=status.HTTP_200_OK)
    def patch(self, request, provider_instance_action_id):
        """
        Return a list of ALL users found on provider_uuid
        """
        data = request.DATA
        try:
           p_instance_action = ProviderInstanceAction.objects.get(id=provider_instance_action_id)
        except ProviderInstanceAction.DoesNotExist:
            return Response("Bad ID", status=status.HTTP_400_BAD_REQUEST)
        serializer = PATCH_ProviderInstanceActionSerializer(p_instance_action, data=data, partial=True)
        if serializer.is_valid():
            p_instance_action = serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
