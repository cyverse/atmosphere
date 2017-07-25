from rest_framework.generics import ListAPIView
from rest_framework.views import APIView
from api.permissions import ApiAuthOptional, ApiAuthRequired, InMaintenance, ProjectMemberRequired


class MaintenanceAPIView(APIView):
    permission_classes = (InMaintenance,)

# NOTE: There should be more strict requirements for 'owner of the Project' to protect "Members of a shared tenant" from interacting (in a bad way) with resources they do not own.
# For now, all access/ACLs are handled in ProjectMemberRequired
class AuthAPIView(MaintenanceAPIView):
    permission_classes = (ApiAuthRequired,
                          InMaintenance,
                          ProjectMemberRequired)


class AuthOptionalAPIView(MaintenanceAPIView):
    permission_classes = (ApiAuthOptional,
                          InMaintenance,)


class MaintenanceListAPIView(ListAPIView):
    permission_classes = (InMaintenance,)


class AuthListAPIView(MaintenanceListAPIView):
    permission_classes = (ApiAuthRequired,
                          InMaintenance,)
