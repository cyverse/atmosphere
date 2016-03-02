import subprocess

from rest_framework.viewsets import ViewSet
from rest_framework.response import Response


class CeleryViewSet(ViewSet):

    """
    API endpoint that prints the status of celery
    """

    def list(self, request):
        """
        At time of request, check the current status
        of celery and return back 'the status'.
        """
        ps = subprocess.Popen(
            ['ps', 'aux'], stdout=subprocess.PIPE)
        output = subprocess.check_output(
            ['grep', '[c]elery worker'], stdin=ps.stdout)

        if output:
            resp = {'status': 200, 'message': "Celery is running"}
            status_code = 200
        else:
            resp = {'status': 404, 'message': "Celery is NOT running"}
            status_code = 404

        return Response(resp, status=status_code)
