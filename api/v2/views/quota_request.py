from rest_framework import viewsets
from core.models import QuotaRequest, Quota, IdentityMembership
from api.v2.serializers.details import QuotaRequestSerializer


class QuotaRequestViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows providers to be viewed or edited.
    """
    queryset = QuotaRequest.objects.all()
    serializer_class = QuotaRequestSerializer

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