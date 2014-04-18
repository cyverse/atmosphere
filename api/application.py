from django.core.paginator import Paginator,\
    PageNotAnInteger, EmptyPage

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from threepio import logger

from core.models import Application as CoreApplication
from core.models import Identity
from core.models.application import visible_applications, public_applications

from service.machine_search import search, CoreApplicationSearch

from authentication.decorators import api_auth_token_optional,\
                                      api_auth_token_required
from api import prepare_driver, failure_response, invalid_creds
from api.permissions import InMaintenance, ApiAuthOptional, ApiAuthRequired
from api.serializers import ApplicationSerializer, PaginatedApplicationSerializer


class ApplicationList(APIView):
    """List of Applications
    """

    serializer_class = ApplicationSerializer
    model = CoreApplication
    permission_classes = (InMaintenance,ApiAuthOptional)

    def get(self, request, **kwargs):
        """
        Using provider and identity, get application list
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
    Detailed view of application
    """
    serializer_class = ApplicationSerializer
    model = CoreApplication
    permission_classes = (ApiAuthRequired,)

    def get(self, request, app_uuid, **kwargs):
        """
        Details of specific application.
        
            app_uuid -- Unique ID for Application

        """
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

    def put(self, request, app_uuid, **kwargs):
        """
        Update specific application

        app_uuid -- Unique ID of application

        """
        user = request.user
        data = request.DATA
        app = CoreApplication.objects.filter(uuid=app_uuid)
        if not app:
            return failure_response(status.HTTP_404_NOT_FOUND,
                                    "Application with uuid %s does not exist"
                                    % app_uuid)
        app = app[0]

    def patch(self, request, app_uuid, **kwargs):
        """
        Update specific application

        app_uuid -- Unique ID of application

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


class ApplicationSearch(APIView):
    """
    Provides server-side Application search for an identity.
    """

    permission_classes = (InMaintenance,)

    @api_auth_token_required
    def get(self, request):
        """
        Search for an application using query.
        
        query -- The search request, performed against Image
                 Name/Description/Tag(s)
        """
        data = request.DATA
        query = request.QUERY_PARAMS.get('query')
        if not query:
            return failure_response(
                status.HTTP_400_BAD_REQUEST,
                "Query not provided.")

        identity_id = request.QUERY_PARAMS.get('identity')
        identity = Identity.objects.filter(id=identity_id)
        #Empty List or identity found..
        if identity:
            identity = identity[0]
        #Okay to search w/ identity=None
        search_result = search([CoreApplicationSearch], query, identity)
        page = request.QUERY_PARAMS.get('page')
        if page:
            paginator = Paginator(search_result, 20)
            try:
                search_page = paginator.page(page)
            except PageNotAnInteger:
                # If page is not an integer, deliver first page.
                search_page = paginator.page(1)
            except EmptyPage:
                # Page is out of range.
                # deliver last page of results.
                search_page = paginator.page(paginator.num_pages)
            serialized_data = \
                PaginatedApplicationSerializer(
                    search_page,
                    context={'request':request}).data
        else:
            serialized_data = ApplicationSerializer(
                search_result,
                context={'request':request}).data
        response = Response(serialized_data)
        response['Cache-Control'] = 'no-cache'
        return response
