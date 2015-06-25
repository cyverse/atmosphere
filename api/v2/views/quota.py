from core.models import Quota

from api.v2.serializers.details import QuotaSerializer
from api.v2.views.base import AuthViewSet


class QuotaViewSet(AuthViewSet):
    """
    API endpoint that allows providers to be viewed or edited.
    """

    queryset = Quota.objects.all()
    serializer_class = QuotaSerializer
    http_method_names = ['get', 'head', 'options', 'trace']
