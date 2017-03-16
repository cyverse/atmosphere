from core.models import RenewalStrategy
from api.v2.serializers.details import RenewalStrategySerializer
from api.v2.views.base import AuthReadOnlyViewSet


class RenewalStrategyViewSet(AuthReadOnlyViewSet):

    """
    API endpoint that allows status types to be viewed.
    """
    lookup_fields = ("id")
    queryset = RenewalStrategy.objects.all()
    serializer_class = RenewalStrategySerializer
