from core.models import Tag

from api.permissions import CloudAdminRequired
from api.v2.serializers.summaries import TagSummarySerializer
from api.v2.views.base import AuthReadOnlyViewSet


class TagViewSet(AuthReadOnlyViewSet):
    """
    API endpoint that allows tags to be viewed or edited.
    """

    queryset = Tag.objects.all()
    serializer_class = TagSummarySerializer
    max_paginate_by = 1000

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_permissions(self):
        if self.request.method in ["POST", "PUT", "DELETE"]:
            self.permission_classes = (CloudAdminRequired,)
        return super(TagViewSet, self).get_permissions()
