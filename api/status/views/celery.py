import subprocess

from rest_framework.viewsets import ViewSet
from rest_framework.response import Response


def _is_celery_running():
    """
    Verify whether or not celery workers are running
    return True/False
    """
    ps = subprocess.Popen(
        ['ps', 'aux'], stdout=subprocess.PIPE)
    try:
        output = subprocess.check_output(
            ['grep', '[c]elery worker'], stdin=ps.stdout)
        return output is not ""
    except subprocess.CalledProcessError:
        # Grep returns exit-code 1 if no match
        return False


class CeleryViewSet(ViewSet):

    """
    API endpoint that prints the status of celery
    """

    def list(self, request):
        """
        At time of request, check the current status
        of celery and return back 'the status'.
        """
        result = _is_celery_running()
        if result:
            resp = {'status': 200, 'message': "Celery is running"}
            status_code = 200
        else:
            resp = {'status': 404, 'message': "Celery is NOT running"}
            status_code = 404

        return Response(resp, status=status_code)
