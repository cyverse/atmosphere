from core.models import ApplicationBookmark as ImageBookmark, Application
from django.utils import timezone
from django.db.models import Q

from api.v2.serializers.details import ImageBookmarkSerializer
from api.v2.views.base import AuthModelViewSet
from api.v2.views.mixins import MultipleFieldLookup


class ImageBookmarkViewSet(MultipleFieldLookup, AuthModelViewSet):

    """
    API endpoint that allows instance actions to be viewed or edited.
    """

    lookup_fields = ("id", "uuid")
    queryset = ImageBookmark.objects.all()
    serializer_class = ImageBookmarkSerializer
    http_method_names = ['get', 'post', 'delete', 'head', 'options', 'trace']

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_queryset(self):
        """
        Filter projects by current user
        """
        user = self.request.user
        now_time = timezone.now()
        application_ids = list(Application.shared_with_user(user).values_list('id', flat=True))
        return ImageBookmark.objects.filter(user=user).filter(
            Q(application__id__in=application_ids)).distinct()
