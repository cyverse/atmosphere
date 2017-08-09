from django.contrib.auth.models import AnonymousUser
from core.models import InstancePlaybookSnapshot, Instance
from core.query import only_current

from api.v2.serializers.details import InstancePlaybookSnapshotSerializer
from api.v2.views.base import AuthModelViewSet


class InstancePlaybookViewSet(AuthModelViewSet):
    """
    API endpoint will return the latest unique 'playbook history' item for a given instance
    """

    queryset = InstancePlaybookSnapshot.objects.all()
    serializer_class = InstancePlaybookSnapshotSerializer
    ordering = ('instance_id', 'playbook_name', 'playbook_arguments')
    ordering_fields = ('instance_id', 'playbook_name', 'playbook_arguments')
    http_method_names = ['get', 'patch', 'head', 'options', 'trace']

    def get_queryset(self):
        """
        Filter out tags for deleted instances
        """
        user = self.request.user
        if isinstance(user, AnonymousUser):
            return InstancePlaybookSnapshot.objects.none()

        instances_qs = Instance.shared_with_user(user)
        if 'archived' not in self.request.query_params:
            instances_qs = instances_qs.filter(only_current())
        instance_ids = instances_qs.values_list('provider_alias', flat=True)
        queryset = InstancePlaybookSnapshot.objects.filter(instance__provider_alias__in=instance_ids)
        return queryset
