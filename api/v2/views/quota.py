from rest_framework.response import Response
from rest_framework import status

from api.v2.serializers.details import QuotaSerializer
from api.v2.views.base import AuthModelViewSet
from api.v2.views.mixins import MultipleFieldLookup
from api.permissions import CloudAdminRequired
from api.pagination import OptionalPagination
from core.models import Quota


class QuotaViewSet(MultipleFieldLookup, AuthModelViewSet):

    """
    API endpoint that allows providers to be viewed or edited.
    NOTE: we have *INTENTIONALLY* left out the ability to *UPDATE* or *DELETE* a quota.
    This can have *disasterous cascade issues* on other fields.
    DO NOT DELETE or UPDATE quota!
    """
    lookup_fields = ("id", "uuid")
    queryset = Quota.objects.all()
    serializer_class = QuotaSerializer
    pagination_class = OptionalPagination
    permission_classes = (
        CloudAdminRequired,
    )
    http_method_names = ['get', 'post', 'head', 'options', 'trace']

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        queryset = self.get_queryset()
        existing = queryset.filter(**serializer.validated_data).first()

        # Since quotas are never mutated, we don't create a quota if it
        # already exists, clients can just POST a quota with values and are
        # guaranteed a successful response (whether or not a quota with the
        # same values already exists)
        if existing:
            serializer = self.get_serializer(existing)
            return Response(serializer.data, status=status.HTTP_200_OK)

        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
