from rest_framework import viewsets
from core.models import QuotaRequest, Quota, IdentityMembership
from api.v2.serializers.details import QuotaRequestSerializer


class QuotaRequestViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows providers to be viewed or edited.
    """
    queryset = QuotaRequest.objects.all()
    serializer_class = QuotaRequestSerializer

    def create(self, request, *args, **kwargs):
        # todo: quota isn't required, but validation is throwing an error
        # set it to *something* for now, figure out what's wrong later...
        quota = Quota.objects.first()
        request.data['quota'] = quota.pk
        return super(viewsets.ModelViewSet, self).create(request, *args, **kwargs)

    def perform_create(self, serializer):
        identity_id = serializer.initial_data.get('identity')
        membership = IdentityMembership.objects.get(identity=identity_id)
        serializer.save(
            membership=membership,
            created_by=self.request.user
        )
