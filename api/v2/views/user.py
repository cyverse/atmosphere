from core.models import AtmosphereUser
from api.v2.serializers.details import UserSerializer
from api.v2.views.base import AuthReadOnlyViewSet


class UserViewSet(AuthReadOnlyViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """

    queryset = AtmosphereUser.objects.all()
    serializer_class = UserSerializer
    filter_fields = ('email',)
    http_method_names = ['get', 'head', 'options', 'trace']
