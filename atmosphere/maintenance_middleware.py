from django.http import JsonResponse
from core.models import MaintenanceRecord


class MaintenanceMiddleware(object):
    """
    This middleware returns a 503 when the app is under maintenance for non-admin users
    """
    
    def process_request(self, request):

        # let staff users through
        if request.user.is_staff:
            return None

        # get active maintenance records with no provider specified
        maintenance_records = MaintenanceRecord.active().filter(provider__isnull=True, disable_login=True)

        # if there are no app disabling records, let users through
        if maintenance_records.count() == 0:
            return None

        # return a 503 status code along with the message from the first record
        content = {
            'message': maintenance_records.first().message
        }
        response = JsonResponse(content)
        response.status_code = 503
        return response
