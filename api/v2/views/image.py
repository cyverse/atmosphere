from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from core.models import Application as Image
from api.v2.serializers.details import ImageSerializer
from django.contrib.auth.models import AnonymousUser
from core.models import AtmosphereUser
from core.models import AtmosphereUser as User


class ImageViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows images to be viewed or edited.
    """
    queryset = Image.objects.all()
    serializer_class = ImageSerializer
    filter_fields = ('created_by__username', 'tags__name')
    search_fields = ('name', 'description', 'tags__name', 'tags__description')
    permission_classes = (IsAuthenticatedOrReadOnly,)
    http_method_names = ['get', 'head', 'options', 'trace']

    def get_queryset(self):
        user = self.request.user

        public_image_set = Image.objects.filter(end_date=None, private=False)

        if isinstance(user, AnonymousUser):
            return public_image_set

        elif isinstance(user, AtmosphereUser):
            member_ids = user.group_set.values_list('id', flat=True)
            user_image_set = Image.objects.filter(created_by=user)
            shared_image_set = Image.objects.filter(members__id__in=member_ids)

            if user.is_staff:
                return Image.objects.all()
            return (public_image_set | user_image_set | shared_image_set).distinct()

        else:
            return Image.objects.none()