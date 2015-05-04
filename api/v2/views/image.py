from itertools import chain

from django.contrib.auth.models import AnonymousUser
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticatedOrReadOnly

from core.models import Application as Image
from core.models import AtmosphereUser
from core.query import only_current, only_current_machines

from api.v2.serializers.details import ImageSerializer


class ImageViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows images to be viewed or edited.
    """
    serializer_class = ImageSerializer
    filter_fields = ('created_by__username', 'tags__name')
    search_fields = ('id', 'name', 'versions__description', 'tags__name', 'tags__description', 'created_by__username')
    permission_classes = (IsAuthenticatedOrReadOnly,)
    http_method_names = ['get', 'head', 'options', 'trace']

    def get_queryset(self):
        request_user = self.request.user
        public_image_set = Image.objects.filter(only_current(), private=False).order_by('-start_date')
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
                only_current_machines(),
                versions__machines__members__id__in=
                    request_user.group_set.values('id'))
            return (public_image_set | my_images | privately_shared).distinct()
        else:
            return Image.objects.none()
