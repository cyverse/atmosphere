from core.models import ProjectExternalLink
from core.query import is_project_member

from api.v2.serializers.details import ProjectExternalLinkSerializer
from api.v2.views.base import ProjectOwnerViewSet


class ProjectExternalLinkViewSet(ProjectOwnerViewSet):

    """
    API endpoint that allows link actions to be viewed or edited.
    """

    queryset = ProjectExternalLink.objects.all()
    serializer_class = ProjectExternalLinkSerializer
    filter_fields = ('project__id',)

    def get_queryset(self):
        """
        Filter out tags for deleted links
        """
        user = self.request.user
        p_links = ProjectExternalLink.objects.filter(is_project_member(user))
        # p_links = ProjectExternalLink.objects.filter(
        #    external_link__created_by=user)
        return p_links
