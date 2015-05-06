from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework import serializers
from core.models import Tag
from api.v2.serializers.summaries import TagSummarySerializer
from api.v2.permissions import IsAdminOrReadOnly


class TagViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows tags to be viewed or edited.
    """
    queryset = Tag.objects.all()
    serializer_class = TagSummarySerializer
    permission_classes = (IsAdminOrReadOnly,)
    max_paginate_by = 1000

    def perform_create(self, serializer):
        same_name_tags = Tag.objects.filter(name__iexact=serializer.validated_data.get('name'))
        if same_name_tags:
            raise serializers.ValidationError('A tag with this name already exists: %s' % same_name_tags.first().name)

        serializer.save(user=self.request.user)

    def get_permissions(self):
        method = self.request.method
        if method == 'POST':
            self.permission_classes = (IsAuthenticatedOrReadOnly,)

        return super(viewsets.ModelViewSet, self).get_permissions()
