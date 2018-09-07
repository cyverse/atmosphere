from django.contrib.auth.models import AnonymousUser
from rest_framework import filters
from core.models import Application as Application
from api.v2.views.base import AuthOptionalViewSet
from api.v2.views.mixins import MultipleFieldLookup
from api.v2.serializers.details import ImageMetricSerializer


class ImageMetricViewSet(MultipleFieldLookup, AuthOptionalViewSet):
    """
    API endpoint that allows instance actions to be viewed or edited.
    """
    lookup_fields = ("id", "uuid")
    queryset = Application.objects.all()
    serializer_class = ImageMetricSerializer
    filter_backends = (filters.OrderingFilter, filters.DjangoFilterBackend)

    def get_queryset(self):
        request_user = self.request.user
        if type(request_user) == AnonymousUser or not request_user.is_staff:
            return Application.objects.none()
        return Application.images_for_user(request_user)
