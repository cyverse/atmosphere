from rest_framework.generics import ListAPIView
from rest_framework.views import APIView
from api.permissions import (
    ApiAuthOptional, ApiAuthRequired, InMaintenance,
    ProjectMemberRequired, ProjectOwnerRequired
)


class MaintenanceAPIView(APIView):
    permission_classes = (InMaintenance,)


class AuthAPIView(MaintenanceAPIView):
    permission_classes = (ApiAuthRequired,
                          InMaintenance,)


class ProjectMemberAPIView(MaintenanceAPIView):
    permission_classes = (ApiAuthRequired,
                          InMaintenance,
                          ProjectMemberRequired)


class ProjectOwnerAPIView(MaintenanceAPIView):
    permission_classes = (ApiAuthRequired,
                          InMaintenance,
                          ProjectOwnerRequired)


class AuthOptionalAPIView(MaintenanceAPIView):
    permission_classes = (ApiAuthOptional,
                          InMaintenance,)


class MaintenanceListAPIView(ListAPIView):
    permission_classes = (InMaintenance,)


class AuthListAPIView(MaintenanceListAPIView):
    permission_classes = (ApiAuthRequired,
                          InMaintenance,)
