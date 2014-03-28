"""
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from threepio import logger

from core.models import Application as CoreApplication
from core.models.application import visible_applications, public_applications

from authentication.decorators import api_auth_token_optional,\
                                      api_auth_token_required
from api import prepare_driver, failure_response, invalid_creds
from api.permissions import InMaintenance
from api.serializers import ApplicationSerializer


class ApplicationList(APIView):
    """
    Represents:
        A Manager of Machine
        Calls to the Machine Class
    TODO: POST when we have programmatic image creation/snapshots
    """

    permission_classes = (InMaintenance,)

    @api_auth_token_optional
    def get(self, request, **kwargs):
        """
        Using provider and identity, getlist of machines
        TODO: Cache this request
        """
        request_user = kwargs.get('request_user')
        applications = public_applications()
        #Concatenate 'visible'
        if request_user:
            my_apps = visible_applications(request_user)
            applications.extend(my_apps)
        serialized_data = ApplicationSerializer(applications,
                                                context={'request':request},
                                                many=True).data
        response = Response(serialized_data)
        return response


class Application(APIView):
    """
    Represents:
        A Manager of Machine
        Calls to the Machine Class
    TODO: POST when we have programmatic image creation/snapshots
    """

    permission_classes = (InMaintenance,)

    @api_auth_token_optional
    def get(self, request, app_uuid, **kwargs):
        app = CoreApplication.objects.filter(uuid=app_uuid)
        if not app:
            return failure_response(status.HTTP_404_NOT_FOUND,
                                    "Application with uuid %s does not exist"
                                    % app_uuid)
        app = app[0]
        serialized_data = ApplicationSerializer(
                app, context={'request':request}).data
        response = Response(serialized_data)
        return response

    @api_auth_token_required
    def put(self, request, app_uuid, **kwargs):
        """
        TODO: Determine who is allowed to edit machines besides
            core_machine.owner
        """
        user = request.user
        data = request.DATA
        app = CoreApplication.objects.filter(uuid=app_uuid)
        if not app:
            return failure_response(status.HTTP_404_NOT_FOUND,
                                    "Application with uuid %s does not exist"
                                    % app_uuid)
        app = app[0]

    @api_auth_token_required
    def patch(self, request, app_uuid, **kwargs):
        """
        TODO: Determine who is allowed to edit machines besides
        core_machine.owner
        """
        user = request.user
        data = request.DATA
        app = CoreApplication.objects.filter(uuid=app_uuid)
        if not app:
            return failure_response(status.HTTP_404_NOT_FOUND,
                                    "Application with uuid %s does not exist"
                                    % app_uuid)
        app = app[0]
        app_owner = app.created_by
        app_members = app.get_members()
        if user != app_owner and not any(group for group
                                         in user.group_set.all()
                                         if group in app_members):
            return failure_response(status.HTTP_403_FORBIDDEN,
                                    "You are not the Application owner. "
                                    "This incident will be reported")
        partial_update = kwargs.get('_partial',True)
        serializer = ApplicationSerializer(app, data=data,
                                           context={'request':request}, 
                                           partial=partial_update)
        if serializer.is_valid():
            logger.info('metadata = %s' % data)
            #TODO: Update application metadata on each machine?
            #update_machine_metadata(esh_driver, esh_machine, data)
            serializer.save()
            logger.info(serializer.data)
            return Response(serializer.data)
        return failure_response(
            status.HTTP_400_BAD_REQUEST,
            serializer.errors)
