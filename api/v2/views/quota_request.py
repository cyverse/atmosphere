from rest_framework import viewsets
from core.models import QuotaRequest, IdentityMembership
from api.v2.serializers.details import QuotaRequestSerializer
from rest_framework.permissions import IsAuthenticated, IsAdminUser


class QuotaRequestViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows providers to be viewed or edited.
    """
    queryset = QuotaRequest.objects.all()
    serializer_class = QuotaRequestSerializer
    permission_classes = (IsAuthenticated,)
    filter_fields = ('status__id', 'status__name')
    http_method_names = ['get', 'post', 'put', 'patch', 'head', 'options', 'trace']

    def perform_create(self, serializer):
        identity_id = serializer.initial_data.get('identity')
        membership = IdentityMembership.objects.get(identity=identity_id)
        serializer.save(
            membership=membership,
            created_by=self.request.user
        )

    def get_queryset(self):
        """
        Filter quota requests by current user
        """
        user = self.request.user
        return QuotaRequest.objects.filter(created_by=user)

    def get_permissions(self):
        method = self.request.method
        if method == 'PUT':
            self.permission_classes = (IsAdminUser,)

        return super(viewsets.ModelViewSet, self).get_permissions()
