from rest_framework.decorators import detail_route
from rest_framework.exceptions import ValidationError
from core.models import Project, Group
from core.query import only_current

from api.v2.serializers.details import ProjectSerializer,\
    VolumeSerializer, InstanceSerializer
from api.v2.views.base import AuthViewSet
from api.v2.views.mixins import MultipleFieldLookup


class ProjectViewSet(MultipleFieldLookup, AuthViewSet):

    """
    API endpoint that allows projects to be viewed or edited.
    """

    lookup_fields = ("id", "uuid")
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer

    def perform_destroy(self, serializer):
        project = self.get_object()
        # Active instances, volumes should prohibit deletion of a project
        if project.instances.filter(end_date__isnull=True).count() > 0:
            raise ValidationError(
                "Cannot delete a project when it contains instances."
                " To delete a project, all instances must be moved "
                "to another project or deleted")
        elif project.applications.filter(end_date__isnull=True).count() > 0:
            raise ValidationError(
                "Cannot delete a project when it contains images."
                " To delete a project, all images must be moved "
                "to another project or removed from the project.")
        elif project.links.all().count() > 0:
            raise ValidationError(
                "Cannot delete a project when it contains external links."
                " To delete a project, all external links must be moved "
                "to another project or deleted")
        elif project.volumes.filter(
                instance_source__end_date__isnull=True).count() > 0:
            raise ValidationError(
                "Cannot delete a project when it contains volumes."
                " To delete a project, all volumes must be moved "
                "to another project or deleted")
        project.delete()

    def perform_create(self, serializer):
        user = self.request.user
        try:
            group = Group.objects.get(name=user.username)
        except Group.DoesNotExist:
            raise ValidationError("Group for %s does not exist." % user.username)
        serializer.save(owner=group)

    def get_queryset(self):
        """
        Filter projects by current user.
        """
        user = self.request.user
        return Project.objects.filter(only_current(),
                                      owner__name=user.username)

    @detail_route()
    def instances(self, *args, **kwargs):
        project = self.get_object()
        self.get_queryset = super(AuthViewSet, self).get_queryset
        self.queryset = project.instances.get_queryset()
        self.serializer_class = InstanceSerializer
        return self.list(self, *args, **kwargs)

    @detail_route()
    def volumes(self, *args, **kwargs):
        project = self.get_object()
        self.get_queryset = super(AuthViewSet, self).get_queryset
        self.queryset = project.volumes.get_queryset()
        self.serializer_class = VolumeSerializer
        return self.list(self, *args, **kwargs)
