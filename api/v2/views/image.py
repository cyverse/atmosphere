from django.contrib.auth.models import AnonymousUser
from django.shortcuts import get_object_or_404

from rest_framework.response import Response

from core.models import Application as Image
from core.models import AtmosphereUser, AccountProvider
from core.query import only_current, only_current_apps

from api import permissions
from api.v2.serializers.details import ImageSerializer
from api.v2.views.base import AuthOptionalViewSet
from api.v2.views.mixins import MultipleFieldLookup


def get_admin_images(request_user):
    # Final query for admins/staff images
    provider_id_list = request_user.identity_set.values_list('provider',
                                                             flat=True)
    # TODO: This 'just works' and is probably very slow... Better way?
    account_providers_list = AccountProvider.objects.filter(
        provider__id__in=provider_id_list)
    admin_users = [ap.identity.created_by for ap in account_providers_list]
    image_ids = []
    for user in admin_users:
        image_ids.extend(
            user.application_set.values_list('id', flat=True))
    admin_list = Image.objects.filter(
        only_current_apps(),
        id__in=image_ids)
    return admin_list


class ImageViewSet(MultipleFieldLookup, AuthOptionalViewSet):

    """
    API endpoint that allows images to be viewed or edited.
    """
    lookup_fields = ("id", "uuid")

    http_method_names = ['get', 'put', 'patch', 'head', 'options', 'trace']

    filter_fields = ('created_by__username', 'tags__name')

    permission_classes = (permissions.InMaintenance,
                          permissions.ApiAuthOptional,
                          permissions.CanEditOrReadOnly,
                          permissions.ApplicationMemberOrReadOnly)

    serializer_class = ImageSerializer

    search_fields = ('id', 'name', 'versions__change_log', 'tags__name', 'tags__description', 'created_by__username')

    def get_queryset(self):
        request_user = self.request.user
        public_image_set = Image.objects.filter(
            only_current(), private=False).order_by('-start_date')
        if isinstance(request_user, AnonymousUser):
            # Anonymous users can only see PUBLIC applications
            # (& their respective images on PUBLIC providers)
            # that have not been end dated by Owner/Admin.
            return public_image_set
        elif isinstance(request_user, AtmosphereUser):
            # All my images (Regardless of 'end dates' or public/private
            my_images = request_user.application_set.all()

            # Non-end dated machines that have
            # been EXPLICITLY shared with me
            member_ids = request_user.group_set.values_list('id', flat=True)
            privately_shared = Image.objects.filter(
                only_current_apps(),
                versions__machines__members__id__in=member_ids)
            if not request_user.is_staff:
                admin_list = Image.objects.none()
            else:
                admin_list = get_admin_images(request_user)

            return (public_image_set | my_images |
                    privately_shared | admin_list).distinct()
        else:
            return Image.objects.none()
