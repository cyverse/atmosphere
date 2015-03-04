from rest_framework import viewsets
from core.models import ApplicationBookmark as ImageBookmark
from api.v2.serializers.details import ImageBookmarkSerializer


class ImageBookmarkViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows instance actions to be viewed or edited.
    """
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
        return ImageBookmark.objects.filter(user=user)
