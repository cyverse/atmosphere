from itertools import chain

from django.contrib.auth.models import AnonymousUser
from django.shortcuts import get_object_or_404

from rest_framework.response import Response

from core.models import Application as Image
from core.models import AtmosphereUser, AccountProvider
from core.query import only_current, only_current_apps

from api.v2.serializers.details import ImageSerializer
from api.v2.views.base import AuthOptionalViewSet


class ImageViewSet(AuthOptionalViewSet):
    """
    API endpoint that allows images to be viewed or edited.
    """
    serializer_class = ImageSerializer
    filter_fields = ('created_by__username', 'tags__name')
    search_fields = ('id', 'name', 'versions__description', 'tags__name', 'tags__description', 'created_by__username')
    http_method_names = ['get', 'head', 'options', 'trace']

    def get_queryset(self):
        request_user = self.request.user
        import ipdb;ipdb.set_trace()
        public_image_set = Image.objects.filter(
            only_current(), private=False).order_by('-start_date')
        if type(request_user) == AnonymousUser:
            # Anonymous users can only see PUBLIC applications
            # (& their respective images on PUBLIC providers)
            # that have not been end dated by Owner/Admin.
            return public_image_set
        elif type(request_user) == AtmosphereUser:
            # All my images (Regardless of 'end dates' or public/private
            my_images = request_user.application_set.all()

            # Non-end dated machines that have
            # been EXPLICITLY shared with me
            privately_shared = Image.objects.filter(
                only_current_apps(),
                versions__machines__members__id__in=
                    request_user.group_set.values_list('id', flat=True))
            if not request_user.is_staff:
                return (public_image_set | my_images | privately_shared).distinct()
            # Final query for admins/staff images
            provider_id_list = request_user.identity_set.values_list('provider',flat=True)
            # TODO: This 'just works' and is probably very slow... Look for a better way?
            account_providers_list = AccountProvider.objects.filter(provider__id__in=provider_id_list)
            admin_users = [ap.identity.created_by for ap in account_providers_list]
            image_ids = []
            for user in admin_users:
                image_ids.extend(
                    user.application_set.values_list('id', flat=True))
            admin_list = Image.objects.filter(
                only_current_apps(),
                id__in=image_ids)
            return (public_image_set | my_images | privately_shared | admin_list).distinct()
        else:
            return Image.objects.none()

    def retrieve(self, request, pk=None):
        queryset = self.get_queryset()
        image = get_object_or_404(queryset, pk=pk)
        serialized = ImageSerializer(image, context={"request": request})
        return Response(serialized.data)
