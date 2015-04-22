from django.http import JsonResponse


class MaintenanceMiddleware(object):
    """
    This middleware returns a 503 when the app is under maintenance for non-admin users
    """
    
    def process_request(self, request):
        content = {
            'message': 'Atmosphere is currently under maintenance'
        }
        response = JsonResponse(content)
        response.status_code = 503
        return response
