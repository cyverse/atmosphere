from rest_framework.generics import ListAPIView
from rest_framework.views import APIView
from api.permissions import ApiAuthOptional, ApiAuthRequired, InMaintenance, ProjectLeaderRequired


class MaintenanceAPIView(APIView):
    permission_classes = (InMaintenance,)

#FIXME: There should be more strict requirements for 'owner of the Project' to protect "Members of a shared tenant" from interacting (in a bad way) with resources they do not own. For now, we allow access to avoid unexpected failure in the UI/API.
class AuthAPIView(MaintenanceAPIView):
    permission_classes = (ApiAuthRequired,
                          InMaintenance,
                          ProjectLeaderRequired)


class AuthOptionalAPIView(MaintenanceAPIView):
    permission_classes = (ApiAuthOptional,
                          InMaintenance,)


class MaintenanceListAPIView(ListAPIView):
    permission_classes = (InMaintenance,)


class AuthListAPIView(MaintenanceListAPIView):
    permission_classes = (ApiAuthRequired,
                          InMaintenance,)
