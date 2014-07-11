from django.core.paginator import Paginator,\
    PageNotAnInteger, EmptyPage
from django.contrib.auth.models import AnonymousUser

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from threepio import logger

from core.models import Application as CoreApplication
from core.models import Identity, Group
from core.models.machine import update_application_owner
from core.models.application import visible_applications, public_applications

from service.search import search, CoreApplicationSearch

from authentication.decorators import api_auth_token_optional,\
                                      api_auth_token_required
from api import prepare_driver, failure_response, invalid_creds
from api.permissions import InMaintenance, ApiAuthOptional, ApiAuthRequired
from api.serializers import ApplicationSerializer, PaginatedApplicationSerializer


class ApplicationList(APIView):
    """
        When this endpoint is called without authentication, a list of 'public' images is returned.
        When the endpoint is called with authentication, that list will include any private images the
        user is authorized to see.

        Applications are a set of one or more images that can
        be uniquely identified by a specific UUID, or more commonly, by Name,
        Description, or Tag(s). 
    """

    serializer_class = ApplicationSerializer
    model = CoreApplication
    permission_classes = (InMaintenance,ApiAuthOptional)

    def get(self, request, **kwargs):
        """Authentication optional, list of applications."""
        request_user = kwargs.get('request_user')
        applications = public_applications()
        #Concatenate 'visible'
        if request.user and type(request.user) != AnonymousUser:
            my_apps = visible_applications(request.user)
            applications.extend(my_apps)
        featured_value = request.QUERY_PARAMS.get('featured')
        if featured_value:
            featured = featured_value.lower() == "true"
            if featured:
                applications = [a for a in applications if a.featured()]
            else:
                applications = [a for a in applications if not a.featured()]
        page = request.QUERY_PARAMS.get('page')
        if page or len(applications) == 0:
            paginator = Paginator(applications, 20,
                                  allow_empty_first_page=True)
        else:
            # return all results.
            paginator = Paginator(applications, len(applications),
                                  allow_empty_first_page=True)
        try:
            app_page = paginator.page(page)
        except PageNotAnInteger:
            # If page is not an integer, deliver first page.
            app_page = paginator.page(1)
        except EmptyPage:
            # Page is out of range.
            # deliver last page of results.
            app_page = paginator.page(paginator.num_pages)
        serialized_data = PaginatedApplicationSerializer(
            app_page,
            context={'request':request}).data
        response = Response(serialized_data)
        response['Cache-Control'] = 'no-cache'
        return response


class Application(APIView):
    """
        Applications are a set of one or more images that can
        be uniquely identified by a specific UUID, or more commonly, by Name,
        Description, or Tag(s). 
    """

    permission_classes = (ApiAuthOptional,)

    def get(self, request, app_uuid, **kwargs):
        """
        Details of specific application.
        Params:app_uuid -- Unique ID of Application

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

        Params:app_uuid -- Unique ID of application
        """
        user = request.user
        data = request.DATA
        app = CoreApplication.objects.filter(uuid=app_uuid)
        if not app:
            return failure_response(status.HTTP_404_NOT_FOUND,
                                    "Application with uuid %s does not exist"
                                    % app_uuid)
        app = app[0]
        return self._update_application(request, app, **kwargs)

    def patch(self, request, app_uuid, **kwargs):
        """
        Update specific application

        Params:app_uuid -- Unique ID of application

        """
        app = CoreApplication.objects.filter(uuid=app_uuid)
        if not app:
            return failure_response(status.HTTP_404_NOT_FOUND,
                                    "Application with uuid %s does not exist"
                                    % app_uuid)
        app = app[0]
        return self._update_application(request, app, **kwargs)

    def _update_application(self, request, app, **kwargs):
        data = request.DATA
        user = request.user
        app_owner = app.created_by
        app_members = app.get_members()
        if user != app_owner and not Group.check_membership(user, app_members):
            return failure_response(status.HTTP_403_FORBIDDEN,
                                    "You are not the Application owner. "
                                    "This incident will be reported")
            #Or it wont.. Up to operations..
        partial_update = True if request.method == 'PATCH' else False
        serializer = ApplicationSerializer(app, data=data,
                                           context={'request':request},
                                           partial=partial_update)
        if serializer.is_valid():
            logger.info('metadata = %s' % data)
            #TODO: Update application metadata on each machine?
            #update_machine_metadata(esh_driver, esh_machine, data)
            serializer.save()
            if 'created_by_identity' in request.DATA:
                identity = serializer.object.created_by_identity
                update_application_owner(core_machine.application, identity)
            logger.info(serializer.data)
            return Response(serializer.data)
        return failure_response(
            status.HTTP_400_BAD_REQUEST,
            serializer.errors)


class ApplicationSearch(APIView):
    """
    Provides server-side Application search for an identity.

    Currently the search expects the Query Param: query
    and the query will be perfomed for matches on: Name, Description, & Tag(s)
    """

    permission_classes = (InMaintenance,ApiAuthOptional)

    def get(self, request):
        """"""
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
        if page or len(search_result) == 0:
            paginator = Paginator(search_result, 20,
                                  allow_empty_first_page=True)
        else:
            page = None
            paginator = Paginator(search_result, len(search_result),
                                  allow_empty_first_page=True)
        try:
            search_page = paginator.page(page)
        except PageNotAnInteger:
            # If page is not an integer, deliver first page.
            search_page = paginator.page(1)
        except EmptyPage:
            # Page is out of range.
            # deliver last page of results.
            search_page = paginator.page(paginator.num_pages)
        serialized_data = PaginatedApplicationSerializer(
            search_page,
            context={'request':request}).data
        response = Response(serialized_data)
        response['Cache-Control'] = 'no-cache'
        return response
