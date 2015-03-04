from rest_framework import viewsets
from core.models import Quota
from ..serializers import QuotaSerializer


class QuotaViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows providers to be viewed or edited.
    """
    queryset = Quota.objects.all()
    serializer_class = QuotaSerializer
    http_method_names = ['get', 'head', 'options', 'trace']
