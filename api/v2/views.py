import django_filters
from rest_framework import viewsets
from rest_framework.decorators import list_route, detail_route
from rest_framework.response import Response
from core.models import Tag, Project, Application as Image, Provider, Identity, Quota, Allocation, Volume, \
    Instance, InstanceAction, VolumeAction
from core.models.user import AtmosphereUser
from .serializers import TagSerializer, UserSerializer, ProjectSerializer, ImageSerializer, ProviderSerializer, \
    IdentitySerializer, QuotaSerializer, AllocationSerializer, VolumeSerializer, InstanceSerializer, \
    InstanceActionSerializer, VolumeActionSerializer


class TagViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows tags to be viewed or edited.
    """
    queryset = Tag.objects.all()
    serializer_class = TagSerializer


class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = AtmosphereUser.objects.all()
    serializer_class = UserSerializer
    filter_fields = ('email',)


class ProjectViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows projects to be viewed or edited.
    """
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer

    @detail_route()
    def instances(self, *args, **kwargs):
        project = self.get_object()
        self.queryset = project.instances.get_queryset()
        self.serializer_class = InstanceSerializer
        return self.list(self, *args, **kwargs)

    @detail_route()
    def volumes(self, *args, **kwargs):
        project = self.get_object()
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


class ProviderViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows providers to be viewed or edited.
    """
    queryset = Provider.objects.all()
    serializer_class = ProviderSerializer


class IdentityViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows providers to be viewed or edited.
    """
    queryset = Identity.objects.all()
    serializer_class = IdentitySerializer


class QuotaViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows providers to be viewed or edited.
    """
    queryset = Quota.objects.all()
    serializer_class = QuotaSerializer


class AllocationViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows providers to be viewed or edited.
    """
    queryset = Allocation.objects.all()
    serializer_class = AllocationSerializer


class VolumeFilter(django_filters.FilterSet):
    min_size = django_filters.NumberFilter(name="size", lookup_type='gte')
    max_size = django_filters.NumberFilter(name="size", lookup_type='lte')

    class Meta:
        model = Volume
        fields = ['provider__id', 'min_size', 'max_size']


class VolumeViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows providers to be viewed or edited.
    """
    queryset = Volume.objects.all()
    serializer_class = VolumeSerializer
    filter_class = VolumeFilter


class InstanceViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows providers to be viewed or edited.
    """
    queryset = Instance.objects.all()
    serializer_class = InstanceSerializer
    filter_fields = ('created_by__id',)


class InstanceActionViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows instance actions to be viewed or edited.
    """
    queryset = InstanceAction.objects.all()
    serializer_class = InstanceActionSerializer


class VolumeActionViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows instance actions to be viewed or edited.
    """
    queryset = VolumeAction.objects.all()
    serializer_class = VolumeActionSerializer

