from api.v2.serializers.details import RenewalStrategySerializer
from api.v2.views.base import AuthReadOnlyViewSet
from cyverse_allocation.cyverse_rules_engine_setup import renewal_strategies


class RenewalStrategyViewSet(AuthReadOnlyViewSet):

    """
    API endpoint that allows status types to be viewed.
    """

    lookup_fields = ("name")
    data = renewal_strategies
    serializer_class = RenewalStrategySerializer

    def get_queryset(self):
        return [(k,v) for k,v in renewal_strategies.iteritems()]