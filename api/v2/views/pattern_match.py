from core.models import PatternMatch

from api.v2.serializers.details import PatternMatchSerializer
from api.v2.views.base import AuthModelViewSet


class PatternMatchViewSet(AuthModelViewSet):
    """
    API endpoint that allows tags to be viewed or edited.
    """
    queryset = PatternMatch.objects.all()
    serializer_class = PatternMatchSerializer

    def get_queryset(self):
        user = self.request.user
        qs = PatternMatch.objects.filter(created_by=user)
        return qs
