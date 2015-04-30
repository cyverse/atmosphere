from core.models import Tag

from api.permissions import CloudAdminRequired
from api.v2.serializers.summaries import TagSummarySerializer
from api.v2.base import AuthOptionalViewSet


class TagViewSet(AuthOptionalViewSet):
    """
    API endpoint that allows tags to be viewed or edited.
    """

    queryset = Tag.objects.all()
    serializer_class = TagSummarySerializer
    max_paginate_by = 1000

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_permissions(self):
        method = self.request.method
        if method == 'DELETE' or method == 'PUT':
            self.permission_classes = (CloudAdminRequired,)
        return super(viewsets.ModelViewSet, self).get_permissions()
