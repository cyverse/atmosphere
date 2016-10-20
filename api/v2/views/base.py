from functools import wraps
from threepio import logger
from django.utils import timezone

from rest_framework import exceptions, status
from rest_framework.decorators import detail_route
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from core import exceptions as core_exceptions
from core.models import IdentityMembership, CloudAdministrator
from core.models.status_type import StatusType

from api.permissions import (
        ApiAuthOptional, ApiAuthRequired, EnabledUserRequired,
        InMaintenance, CloudAdminRequired
    )
from api.v2.views.mixins import MultipleFieldLookup


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
            raise exceptions.NotAuthenticated(detail=message)
        if not staff_can_act and (hasattr(instance, "is_closed") and instance.is_closed()):
            message = (
                "Method '%s' not allowed: "
                "the request has already been resolved "
                "and cannot be modified by a non-staff user."
                % self.request.method
            )
            raise exceptions.MethodNotAllowed(self.request.method,
                                              detail=message)
        else:
            return fn(self, request, *args, **kwargs)
    return wrapper


class AuthViewSet(ModelViewSet):
    http_method_names = ['get', 'put', 'patch', 'post',
                         'delete', 'head', 'options', 'trace']
    permission_classes = (InMaintenance,
                          EnabledUserRequired,
                          ApiAuthRequired,)


class AdminAuthViewSet(AuthViewSet):
    permission_classes = (InMaintenance,
                          CloudAdminRequired,
                          EnabledUserRequired,
                          ApiAuthRequired,)


class AuthOptionalViewSet(ModelViewSet):

    permission_classes = (InMaintenance,
                          ApiAuthOptional,)


class AuthReadOnlyViewSet(ReadOnlyModelViewSet):

    permission_classes = (InMaintenance,
                          ApiAuthOptional,)


class OwnerUpdateViewSet(AuthViewSet):
    """
    Base class ViewSet to handle the case where a normal user should see 'GET'
    and an owner (or admin) should be allowed to PUT or PATCH
    """

    http_method_names = ['get', 'put', 'patch', 'post',
                         'delete', 'head', 'options', 'trace']

    @property
    def allowed_methods(self):
        raise Exception("The @property-method 'allowed_methods' should be"
                        " handled by the subclass of OwnerUpdateViewSet")


class BaseRequestViewSet(MultipleFieldLookup, AuthViewSet):

    """
    Base class ViewSet to handle requests
    """

    admin_serializer_class = None
    model = None
    lookup_fields = ("id", "uuid")

    def get_queryset(self):
        """
        Return users requests or all the requests if the user is an admin.
        """
        assert self.model is not None, (
            "%s should include a `model` attribute."
            % self.__class__.__name__
        )
        if self.request.user.is_staff:
            return self.model.objects.all().order_by('-start_date')
        return self.model.objects.filter(created_by=self.request.user).order_by('-start_date')

    def get_serializer_class(self):
        """
        Return the `serializer_class` or `admin_serializer_class`
        given the users privileges.
        """
        assert self.admin_serializer_class is not None, (
            "%s should include an `admin_serializer_class` attribute."
            % self.__class__.__name__
        )
        http_method = self.request._request.method
        if http_method != 'POST' and self.request.user.is_staff:
            return self.admin_serializer_class
        return self.serializer_class

    def perform_create(self, serializer):
        # NOTE: An identity could possible have multiple memberships
        # It may be better to directly take membership rather than an identity
        identity_id = serializer.initial_data.get("identity")
        status, _ = StatusType.objects.get_or_create(name="pending")
        try:
            # NOTE: This is *NOT* going to be a sufficient query when sharing..
            membership = IdentityMembership.objects.get(identity=identity_id)
            instance = serializer.save(
                membership=membership,
                status=status,
                created_by=self.request.user
            )
            if serializer.initial_data.get("admin_url"):
                admin_url = serializer.initial_data.get("admin_url") + str(instance.id)
                self.submit_action(instance, options={"admin_url": admin_url})
            else: 
                self.submit_action(instance)
        except (core_exceptions.ProviderLimitExceeded,  # NOTE: DEPRECATED -- REMOVE SOON, USE BELOW.
                core_exceptions.RequestLimitExceeded):
            message = "Only one active request is allowed per provider."
            raise exceptions.MethodNotAllowed('create', detail=message)
        except core_exceptions.InvalidMembership:
            message = (
                "The user '%s' is not a valid member."
                % self.request.user.username
            )
            raise exceptions.ParseError(detail=message)
        except IdentityMembership.DoesNotExist:
            message = (
                "The identity '%s' does not have a membership"
                % identity_id
            )
            raise exceptions.ParseError(detail=message)
        except Exception as e:
            message = str(e)
            raise exceptions.ParseError(detail=message)

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
            raise exceptions.ParseError(detail=message)

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
            raise ValidationError(
                "Request unknown. "
                "Could not approve request."
            )
        if not serializer.is_valid():
            raise ValidationError(
                "Serializer could not be validated: %s"
                "Could not approve request."
                % (serializer.errors,)
            )
        approve_status = StatusType.objects.get(name='approved')
        request_obj = serializer.save(status=approve_status)
        self.approve_action(request_obj)
        return Response(serializer.data)

    @detail_route()
    def deny(self, *args, **kwargs):
        """
        #FIXME: Both of these actions do something similar, they also 'create and abuse' serializers. Is there a better way to handle this? Lets lok into how `create` vs `perform_create` is called in a DRF 'normal' view.
        """
        request_obj = self.get_object()
        SerializerCls = self.get_serializer_class()
        if not request_obj:
            raise ValidationError(
                "Request unknown. "
                "Could not deny request."
            )
        # Mocking a validation of data...
        serializer = SerializerCls(
            request_obj, data={}, partial=True,
            context={'request': self.request})
        if not serializer.is_valid():
            raise ValidationError(
                "Serializer could not be validated: %s"
                "Could not deny request."
                % (serializer.errors,)
            )
        deny_status = StatusType.objects.get(name='denied')
        request_obj = serializer.save(status=deny_status)
        self.deny_action(request_obj)
        return Response(serializer.data)

    def perform_destroy(self, instance):
        """
        Add an end date to a request and take no further action
        """
        status, _ = StatusType.objects.get_or_create(name="closed")
        instance.status = status
        instance.end_date = timezone.now()
        instance.save()

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
            raise exceptions.MethodNotAllowed('create', detail=message)
        except core_exceptions.InvalidMembership:
            message = (
                "The user '%s' is not a valid member."
                % self.request.user.username
            )
            raise exceptions.ParseError(detail=message)
        except IdentityMembership.DoesNotExist:
            message = (
                "The identity '%s' does not have a membership"
                % identity_id
            )
            raise exceptions.ParseError(detail=message)
        except Exception as e:
            message = {
                "An error was encoutered when updating the request: %s" % e.message
            }
            logger.exception(e)
            raise exceptions.ParseError(detail=message)


    @unresolved_requests_only
    def update(self, request, *args, **kwargs):
        """
        Update the request for the specific identifier
        """
        return super(BaseRequestViewSet, self).update(request, *args, **kwargs)

    def approve_action(self, instance):
        """
        Perform the approved action for the request
        """

    def deny_action(self, instance):
        """
        Perform the denied action for the request
        """

    def submit_action(self, instance):
        """
        Perform the submit action for a new request
        """
