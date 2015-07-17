from django.db.models import Q
from django.contrib.auth.models import AnonymousUser

import django_filters

from core.models import ApplicationVersion as ImageVersion
from core.models import AccountProvider
from core.query import only_current_machines_in_version, only_current

from api.v2.views.base import AuthOptionalViewSet
from api.v2.serializers.details import ImageVersionSerializer


def get_admin_image_versions(user):
    """
    TODO: This 'just works' and is probably very slow... Look for a better way?
    """
    provider_id_list = user.identity_set.values_list('provider', flat=True)
    account_providers_list = AccountProvider.objects.filter(
        provider__id__in=provider_id_list)
    admin_users = [ap.identity.created_by for ap in account_providers_list]
    version_ids = []
    for user in admin_users:
        version_ids.extend(
            user.applicationversion_set.values_list('id', flat=True))
    admin_list = ImageVersion.objects.filter(
        only_current(),
        only_current_machines_in_version(),
        id__in=version_ids)
    return admin_list

class ImageFilter(django_filters.FilterSet):
    image_id = django_filters.CharFilter('application__id')
    created_by = django_filters.CharFilter('application__created_by__username')

class ImageVersionViewSet(AuthOptionalViewSet):

    """
    API endpoint that allows instance actions to be viewed or edited.
    """
    queryset = ImageVersion.objects.all()
    serializer_class = ImageVersionSerializer
    search_fields = ('application__id', 'application__created_by__username')
    filter_class = ImageFilter

    def get_queryset(self):
        request_user = self.request.user

        # Showing non-end dated, public ImageVersions
        public_set = ImageVersion.objects.filter(
            only_current(),
            only_current_machines_in_version(),
            application__private=False)
        if not isinstance(request_user, AnonymousUser):
            # NOTE: Showing 'my pms EVEN if they are end-dated.
            my_set = ImageVersion.objects.filter(
                Q(application__created_by=request_user) |
                Q(machines__instance_source__created_by=request_user))
            all_group_ids = request_user.group_set.values('id')
            # Showing non-end dated, shared ImageVersions
            shared_set = ImageVersion.objects.filter(
                only_current(), only_current_machines_in_version(), Q(
                    membership=all_group_ids) | Q(
                    machines__members__in=all_group_ids))
            if request_user.is_staff:
                admin_set = get_admin_image_versions(request_user)
            else:
                admin_set = ImageVersion.objects.none()
        else:
            admin_set = shared_set = my_set = ImageVersion.objects.none()

        # Order them by date, make sure no dupes.
        return (public_set | shared_set | my_set | admin_set).distinct().order_by(
            '-machines__instance_source__start_date')
