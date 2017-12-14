from core.models import EventTable, Instance

from api.v2.serializers.details import InstancePlaybookHistorySerializer
from core.events.serializers.instance_playbook_history import get_history_list_for_user, get_history_list_for_instance
from api.v2.views.base import AuthReadOnlyViewSet


class InstancePlaybookHistoryViewSet(AuthReadOnlyViewSet):

    """
    API endpoint will return every 'playbook history' item for a given instance
    """
    queryset = EventTable.instance_history_playbooks.all()
    serializer_class = InstancePlaybookHistorySerializer
    ordering = ('entity_id', '-timestamp')
    ordering_fields = ('entity_id', '-timestamp')

    def get(self):
        """
        Disables calls to /v2/instance_playbook_histories/##
        """
        return None

    def get_queryset(self):
        """
        Filter out tags for deleted instances
        """
        username = self.request.user.username
        archived = self.request.query_params\
            .get('archived', "").lower() == 'true'
        instance_id = self.request.query_params.get('instance_id')
        if instance_id:
            return get_history_list_for_instance(instance_id)
        playbook_history_list = get_history_list_for_user(
            username, archived=archived)
        return playbook_history_list
