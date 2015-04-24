from rest_framework.generics import ListAPIView
from rest_framework.views import APIView
from api.permissions import ApiAuthRequired, InMaintenance


class MaintenanceAPIView(APIView):
    permission_classes = (InMaintenance,)


class AuthAPIView(MaintenanceAPIView):
    permission_classes = (ApiAuthRequired,
                          InMaintenance,)


class MaintenanceListAPIView(ListAPIView):
    permission_classes = (InMaintenance,)


class AuthListAPIView(MaintenanceListAPIView):
    permission_classes = (ApiAuthRequired,
                          InMaintenance,)
