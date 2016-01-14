from rest_framework.serializers import ValidationError

from core.models import Tag

from api.permissions import ApiAuthRequired, CloudAdminRequired,\
    InMaintenance
from api.v2.serializers.summaries import TagSummarySerializer
from api.v2.views.base import AuthOptionalViewSet
from api.v2.views.mixins import MultipleFieldLookup


class TagViewSet(MultipleFieldLookup, AuthOptionalViewSet):

    """
    API endpoint that allows tags to be viewed or edited.
    """
    lookup_fields = ("id", "uuid")
    queryset = Tag.objects.all()
    serializer_class = TagSummarySerializer

    def perform_create(self, serializer):
        same_name_tags = Tag.objects.filter(
            name__iexact=serializer.validated_data.get("name"))
        if same_name_tags:
            raise ValidationError("A tag with this name already exists: %s" %
                                  same_name_tags.first().name)
        serializer.save(user=self.request.user)

    def get_permissions(self):
        if self.request.method is "":
            self.permission_classes = (ApiAuthRequired,
                                       InMaintenance,)
        if self.request.method in ["PUT", "PATCH", "DELETE"]:
            self.permission_classes = (CloudAdminRequired,
                                       InMaintenance,)
        return super(TagViewSet, self).get_permissions()
