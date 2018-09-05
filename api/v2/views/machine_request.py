from functools import wraps
from rest_framework import exceptions as rest_exceptions
from rest_framework import status
from rest_framework.decorators import detail_route
from rest_framework.response import Response
from api.v2.serializers.details import MachineRequestSerializer,\
    UserMachineRequestSerializer
from api.v2.views.base import AuthModelViewSet

from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

from django.conf import settings

from core import exceptions as core_exceptions
from core.models import (
    MachineRequest, IdentityMembership, CloudAdministrator, AtmosphereUser,
    Provider, ProviderMachine, Tag
)
from core.models.status_type import StatusType
from core.email import requestImaging

from service.machine import share_with_admins, share_with_self, remove_duplicate_users
from service.tasks.machine import start_machine_imaging
from api.v2.views.mixins import MultipleFieldLookup
from threepio import logger


def unresolved_requests_only(fn):
    """
    Only allow an unresolved request to be processed.
    """
    @wraps(fn)
    def wrapper(self, request, *args, **kwargs):
        instance = self.get_object()
        staff_can_act = request.user.is_staff or request.user.is_superuser or CloudAdministrator.objects.filter(user=request.user.id).exists()
        user_can_act = request.user == getattr(instance, 'created_by')
        if not (user_can_act or staff_can_act):
            message = (
                "Method '%s' not allowed: "
                "Only staff members and the owner are authorized to make this request."
                % self.request.method
            )
            raise rest_exceptions.NotAuthenticated(detail=message)
        if not staff_can_act and (hasattr(instance, "is_closed") and instance.is_closed()):
            message = (
                "Method '%s' not allowed: "
                "the request has already been resolved "
                "and cannot be modified by a non-staff user."
                % self.request.method
            )
            raise rest_exceptions.MethodNotAllowed(self.request.method,
                                              detail=message)
        else:
            return fn(self, request, *args, **kwargs)
    return wrapper


class MachineRequestViewSet(MultipleFieldLookup, AuthModelViewSet):
    queryset = MachineRequest.objects.none()
    model = MachineRequest
    serializer_class = UserMachineRequestSerializer
    admin_serializer_class = MachineRequestSerializer
    lookup_fields = ("id", "uuid")
    filter_fields = ('status__id', 'status__name', 'new_machine_owner__username')
    ordering_fields = ('start_date', 'end_date', 'new_machine_owner__username')
    ordering = ('-start_date',)

    @detail_route()
    def deny(self, *args, **kwargs):
        """
        #FIXME: Both of these actions do something similar, they also 'create and abuse' serializers. Is there a better way to handle this? Lets lok into how `create` vs `perform_create` is called in a DRF 'normal' view.
        """
        request_obj = self.get_object()
        SerializerCls = self.get_serializer_class()
        if not request_obj:
            raise rest_exceptions.ValidationError(
                "Request unknown. "
                "Could not deny request."
            )
        # Mocking a validation of data...
        serializer = SerializerCls(
            request_obj, data={}, partial=True,
            context={'request': self.request})
        if not serializer.is_valid():
            raise rest_exceptions.ValidationError(
                "Serializer could not be validated: %s"
                "Could not deny request."
                % (serializer.errors,)
            )
        deny_status, _ = StatusType.objects.get_or_create(name='denied')
        request_obj = serializer.save(status=deny_status)
        self.deny_action(request_obj)
        return Response(serializer.data)

    @detail_route()
    def approve(self, *args, **kwargs):
        """
        See the deny docs
        """
        request_obj = self.get_object()
        SerializerCls = self.get_serializer_class()
        serializer = SerializerCls(
            request_obj, context={'request': self.request})
        if not request_obj:
            raise rest_exceptions.ValidationError(
                "Request unknown. "
                "Could not approve request."
            )
        if not serializer.is_valid():
            raise rest_exceptions.ValidationError(
                "Serializer could not be validated: %s"
                "Could not approve request."
                % (serializer.errors,)
            )
        approve_status, _ = StatusType.objects.get_or_create(name='approved')
        request_obj = serializer.save(status=approve_status)
        self.approve_action(request_obj)
        return Response(serializer.data)

    @unresolved_requests_only
    def perform_update(self, serializer):
        """
        Updates the request and performs any update actions.
        """
        # NOTE: An identity could possible have multiple memberships
        # It may be better to directly take membership rather than an identity
        identity = serializer.initial_data.get('identity', {})
        membership = None

        if isinstance(identity, dict):
            identity_id = identity.get("id", None)
        else:
            identity_id = identity

        try:
            if identity_id is not None:
                membership = IdentityMembership.objects.get(
                    identity=identity_id)

            if membership:
                instance = serializer.save(end_date=timezone.now(),
                                           membership=membership)
            else:
                if self.request.method == "PATCH":
                    instance = serializer.save(status=StatusType.objects.get(id=serializer.initial_data['status']))
                else:
                    instance = serializer.save()
            if instance.is_approved():
                self.approve_action(instance)

            if instance.is_closed():
                self.close_action(instance)

            if instance.is_denied():
                self.deny_action(instance)
        except (core_exceptions.ProviderLimitExceeded,  # NOTE: DEPRECATED -- REMOVE SOON, USE BELOW.
                core_exceptions.RequestLimitExceeded):
            message = "Only one active request is allowed per provider."
            raise rest_exceptions.MethodNotAllowed('create', detail=message)
        except core_exceptions.InvalidMembership:
            message = (
                "The user '%s' is not a valid member."
                % self.request.user.username
            )
            raise rest_exceptions.ParseError(detail=message)
        except IdentityMembership.DoesNotExist:
            message = (
                "The identity '%s' does not have a membership"
                % identity_id
            )
            raise rest_exceptions.ParseError(detail=message)
        except Exception as e:
            message = {
                "An error was encoutered when updating the request: %s" % e.message
            }
            logger.exception(e)
            raise rest_exceptions.ParseError(detail=message)

    def perform_destroy(self, instance):
        """
        Add an end date to a request and take no further action
        """
        status, _ = StatusType.objects.get_or_create(name="closed")
        instance.status = status
        instance.end_date = timezone.now()
        instance.save()

    @unresolved_requests_only
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        try:
            self.perform_destroy(instance)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            message = {
                "An error was encoutered when closing the request: %s" % e.message
            }
            logger.exception(e)
            raise rest_exceptions.ParseError(detail=message)

    def get_serializer_class(self):
        """
        Return the `serializer_class` or `admin_serializer_class`
        given the users privileges.
        """
        assert self.admin_serializer_class is not None, (
            "%s should include an `admin_serializer_class` attribute."
            % self.__class__.__name__
        )
        # NOTE: Special case! If we are querying for 'user-facing-view' _as a
        # staff user_ we will see something different than normal users. This
        # line will keep consistency, but is admittedly fragile. A better
        # solution would be to _include_ ?admin=true or some other queryparam
        # when the admin_serializer_class is desired _or_ splitting into two
        # endpoints.
        if self.request.query_params.get('new_machine_owner__username','') != '':
            return self.serializer_class

        http_method = self.request._request.method
        if http_method != 'POST' and self.request.user.is_staff:
            return self.admin_serializer_class
        return self.serializer_class

    def get_queryset(self):
        request_user = self.request.user
        if 'active' in self.request.query_params:
            all_active = MachineRequest.objects.filter(
                (
                    ~Q(status__name__in=['closed', 'completed', 'denied']) |
                    Q(start_date__gt=timezone.now() - timedelta(days=7))
                )
            )
            # NOTE: Special case! If we are querying for 'user-facing-view'
            # _as a staff user_ we will get back all the results rather than
            # only our own. This line will keep consistency, but is admittedly
            # fragile. A better solution would be to _include_ ?admin=true or
            # some other queryparam when the entire machine-request-list is
            # desired _or_ splitting into two endpoints.
            if self.request.query_params.get('new_machine_owner__username','') == '' and request_user.is_staff:
                return all_active.order_by('-start_date')
            return all_active.filter(
                created_by=request_user
                ).order_by('-start_date')
        return super(MachineRequestViewSet, self).get_queryset()

    def _get_new_provider(self):
        """
        NOTE: This is a hotfix to ensure the replication provider location is always selected.
        In the future, we will fix this by:
        Creating a strategy for "Provider Groupings" that handles image replication
        This will also be handy because we have a "Provider Grouping" that has a "shared" allocation source as part of their strategy.
        """
        try:
            new_provider = Provider.objects.get(
                location=settings.REPLICATION_PROVIDER_LOCATION)
            return new_provider
        except:
            raise Exception("settings.REPLICATION_PROVIDER_LOCATION could not be set. Contact a developer.")

    def filter_tags(self, user, tag_names):
        new_tag_names = []
        for tag in sorted(tag_names.split(", ")):
            core_tag = Tag.objects.filter(name__iexact=tag).first()
            if not core_tag:
                continue
            if not core_tag.allow_access(user):
                continue
            new_tag_names.append(tag)
        return ", ".join(new_tag_names)

    def perform_create(self, serializer):
        request_user = self.request.user
        q = MachineRequest.objects.filter(
            (
                Q(created_by__id=request_user.id) &
                Q(instance_id=serializer.validated_data['instance'].id) &
                ~Q(status__name="failed") &
                ~Q(status__name="denied") &
                ~Q(status__name="completed") &
                ~Q(status__name="closed")
            ))

        if len(q) > 0:
            message = "Only one active request is allowed per provider."
            raise rest_exceptions.MethodNotAllowed('create', detail=message)
        # NOTE: An identity could possible have multiple memberships
        # It may be better to directly take membership rather than an identity
        identity_id = serializer.initial_data.get("identity")
        parent_machine = serializer.validated_data['instance'].provider_machine
        access_list_usernames = serializer.initial_data.get("access_list") or ""
        access_list = access_list_usernames.split(",")
        visibility = serializer.initial_data.get("new_application_visibility")
        new_provider = self._get_new_provider()
        if  visibility in ["select", "private"]:
            share_with_admins(access_list, parent_machine.provider.uuid)
            share_with_self(access_list, request_user.username)
            access_list = remove_duplicate_users(access_list)

        status, _ = StatusType.objects.get_or_create(name="pending")
        new_machine_provider = Provider.objects.filter(id=new_provider.id)
        new_machine_owner = AtmosphereUser.objects.filter(id=request_user.id)
        parent_machine = ProviderMachine.objects.filter(id=parent_machine.id)

        if new_machine_provider.count():
            new_machine_provider = new_machine_provider[0]
        else:
            raise rest_exceptions.ParseError(detail="Could not retrieve new machine provider.")

        if new_machine_owner.count():
            new_machine_owner = new_machine_owner[0]
        else:
            raise rest_exceptions.ParseError(detail="Could not retrieve new machine owner.")

        if parent_machine.count():
            parent_machine = parent_machine[0]
        else:
            raise rest_exceptions.ParseError(detail="Could not retrieve parent machine.")
        new_tags = self.filter_tags(request_user, serializer.validated_data.get("new_version_tags",""))
        try:
            membership = IdentityMembership.objects.get(identity=identity_id)
            instance = serializer.save(
                membership=membership,
                status=status,
                created_by=request_user,
                new_machine_provider=new_provider,
                new_machine_owner=request_user,
                new_version_tags=new_tags,
                access_list=access_list,
                old_status="pending",  # TODO: Is this required or will it default to pending?
                parent_machine=parent_machine
            )
            instance.migrate_access_to_membership_list(access_list)
            self.submit_action(instance)
        except (core_exceptions.ProviderLimitExceeded,
                core_exceptions.RequestLimitExceeded):
            message = "Only one active request is allowed per provider."
            raise rest_exceptions.MethodNotAllowed('create', detail=message)
        except core_exceptions.InvalidMembership:
            message = (
                "The user '%s' is not a valid member."
                % request_user.username
            )
            raise rest_exceptions.ParseError(detail=message)
        except IdentityMembership.DoesNotExist:
            message = (
                "The identity '%s' does not have a membership"
                % identity_id
            )
            raise rest_exceptions.ParseError(detail=message)
        except Exception as e:
            message = {
                "An error was encoutered when submitting the request: %s" % e.message
            }
            logger.exception(e)
            raise rest_exceptions.ParseError(detail=message)

    def submit_action(self, instance):
        """
        Submits a resource request email
        """
        #NOTE/FIXME: This should be considered when locking down "Imaging Strategy" for a "Provider Grouping"
        new_provider = self._get_new_provider()
        pre_approved = new_provider.auto_imaging
        requestImaging(self.request, instance.id, auto_approve=pre_approved)

        if pre_approved:
            status, _ = StatusType.objects.get_or_create(name="approved")
            instance.status = status
            instance.save()
            start_machine_imaging(instance)

    def approve_action(self, instance):
        """
        Updates the resource for the request
        """
        start_machine_imaging(instance)

    def deny_action(self, instance):
        """
        TODO: Notify the user that the request was denied
        """
        pass

    def close_action(self, instance):
        """
        Silently close request
        """
        pass
