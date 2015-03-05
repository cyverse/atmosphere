from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated, IsAdminUser
from rest_framework.decorators import detail_route
from core.models import Tag, Project, Application as Image, Provider, Identity, Quota, Allocation, Volume, \
    Instance, ProviderType, PlatformType, ProviderMachine, ApplicationBookmark as ImageBookmark, Group, \
    Size, AtmosphereUser
from .serializers import TagSerializer, UserSerializer, ProjectSerializer, ImageSerializer, ProviderSerializer, \
    IdentitySerializer, QuotaSerializer, AllocationSerializer, VolumeSerializer, InstanceSerializer, \
    ProviderTypeSerializer, PlatformTypeSerializer, ProviderMachineSerializer, ImageBookmarkSerializer, \
    SizeSerializer, SizeSummarySerializer, TagSummarySerializer
from core.query import only_current, only_current_source


class TagViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows tags to be viewed or edited.
    """
    queryset = Tag.objects.all()
    serializer_class = TagSummarySerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_permissions(self):
        method = self.request.method
        if method == 'DELETE' or method == 'PUT':
            self.permission_classes = (IsAdminUser,)

        return super(viewsets.ModelViewSet, self).get_permissions()


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = AtmosphereUser.objects.all()
    serializer_class = UserSerializer
    filter_fields = ('email',)
    http_method_names = ['get', 'head', 'options', 'trace']


class ProjectViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows projects to be viewed or edited.
    """
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer

    def perform_create(self, serializer):
        user = self.request.user
        group = Group.objects.get(name=user.username)
        serializer.save(owner=group)

    def get_queryset(self):
        """
        Filter projects by current user
        """
        user = self.request.user
        return Project.objects.filter(only_current(), owner__name=user.username)

    @detail_route()
    def instances(self, *args, **kwargs):
        project = self.get_object()
        self.get_queryset = super(viewsets.ModelViewSet, self).get_queryset
        self.queryset = project.instances.get_queryset()
        self.serializer_class = InstanceSerializer
        return self.list(self, *args, **kwargs)

    @detail_route()
    def volumes(self, *args, **kwargs):
        project = self.get_object()
        self.get_queryset = super(viewsets.ModelViewSet, self).get_queryset
        self.queryset = project.volumes.get_queryset()
        self.serializer_class = VolumeSerializer
        return self.list(self, *args, **kwargs)


class ImageViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows images to be viewed or edited.
    """
    queryset = Image.objects.all()
    serializer_class = ImageSerializer
    filter_fields = ('created_by__username', 'tags__name')
    search_fields = ('name', 'description')
    permission_classes = (IsAuthenticatedOrReadOnly,)
    http_method_names = ['get', 'head', 'options', 'trace']


class ProviderViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows providers to be viewed or edited.
    """
    queryset = Provider.objects.all()
    serializer_class = ProviderSerializer
    permission_classes = (IsAuthenticated,)
    http_method_names = ['get', 'head', 'options', 'trace']

    def get_permissions(self):
        method = self.request.method
        if method == 'DELETE' or method == 'PUT':
            self.permission_classes = (IsAdminUser,)

        return super(viewsets.GenericViewSet, self).get_permissions()

    def get_queryset(self):
        """
        Filter projects by current user
        """
        user = self.request.user
        group = Group.objects.get(name=user.username)
        return group.providers.filter(only_current(), active=True)

    @detail_route()
    def sizes(self, *args, **kwargs):
        provider = self.get_object()
        self.get_queryset = super(viewsets.ModelViewSet, self).get_queryset
        self.queryset = provider.size_set.get_queryset()
        self.serializer_class = SizeSummarySerializer
        return self.list(self, *args, **kwargs)


class IdentityViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows providers to be viewed or edited.
    """
    queryset = Identity.objects.all()
    serializer_class = IdentitySerializer
    http_method_names = ['get', 'head', 'options', 'trace']

    def get_queryset(self):
        """
        Filter identities by current user
        """
        user = self.request.user
        group = Group.objects.get(name=user.username)
        providers = group.providers.filter(only_current(), active=True)
        return user.identity_set.filter(provider__in=providers)


class QuotaViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows providers to be viewed or edited.
    """
    queryset = Quota.objects.all()
    serializer_class = QuotaSerializer
    http_method_names = ['get', 'head', 'options', 'trace']


class AllocationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows providers to be viewed or edited.
    """
    queryset = Allocation.objects.all()
    serializer_class = AllocationSerializer
    http_method_names = ['get', 'head', 'options', 'trace']


#class VolumeFilter(django_filters.FilterSet):
#    min_size = django_filters.NumberFilter(name="size", lookup_type='gte')
#    max_size = django_filters.NumberFilter(name="size", lookup_type='lte')
#
#    class Meta:
#        model = Volume
#        fields = ['min_size', 'max_size']


class VolumeViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows providers to be viewed or edited.
    """
    queryset = Volume.objects.all()
    serializer_class = VolumeSerializer
    # filter_class = VolumeFilter

    def get_queryset(self):
        """
        Filter projects by current user
        """
        user = self.request.user
        return Volume.objects.filter(only_current_source(),
                                     instance_source__created_by=user)


class InstanceViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows providers to be viewed or edited.
    """
    queryset = Instance.objects.all()
    serializer_class = InstanceSerializer
    filter_fields = ('created_by__id',)

    def get_queryset(self):
        """
        Filter projects by current user
        """
        user = self.request.user
        return Instance.objects.filter(only_current(), created_by=user)


class ProviderTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows instance actions to be viewed or edited.
    """
    queryset = ProviderType.objects.all()
    serializer_class = ProviderTypeSerializer
    http_method_names = ['get', 'head', 'options', 'trace']


class PlatformTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows instance actions to be viewed or edited.
    """
    queryset = PlatformType.objects.all()
    serializer_class = PlatformTypeSerializer
    http_method_names = ['get', 'head', 'options', 'trace']


class ProviderMachineViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows instance actions to be viewed or edited.
    """
    queryset = ProviderMachine.objects.all()
    serializer_class = ProviderMachineSerializer


class ImageBookmarkViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows instance actions to be viewed or edited.
    """
    queryset = ImageBookmark.objects.all()
    serializer_class = ImageBookmarkSerializer
    http_method_names = ['get', 'post', 'delete', 'head', 'options', 'trace']

    def get_queryset(self):
        """
        Filter projects by current user
        """
        user = self.request.user
        return ImageBookmark.objects.filter(user=user)


class SizeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows instance actions to be viewed or edited.
    """
    queryset = Size.objects.all()
    serializer_class = SizeSerializer

    def get_queryset(self):
        """
        Filter projects by current user
        """
        user = self.request.user
        group = Group.objects.get(name=user.username)
        providers = group.providers.filter(only_current(), active=True)
        return Size.objects.filter(only_current(), provider__in=providers)
