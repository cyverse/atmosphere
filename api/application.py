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

from api import failure_response
from api.permissions import InMaintenance, ApiAuthOptional
from api.serializers import ApplicationThresholdSerializer,\
    ApplicationSerializer, PaginatedApplicationSerializer

def _filter_applications(applications, user, params):
    #Filter the list based on query strings
    #DB Queryset modifications
    for filter_key, value in params.items():
        if 'start_date' == filter_key:
            applications = applications.filter(
                start_date__gt=value)
        elif 'end_date' == filter_key:
            applications = applications.filter(
                Q(end_date=None) |
                Q(end_date__lt=value))
        elif 'tag' == filter_key:
            applications = applications.filter(
                tags__name=value)
    #List comprehensions 
    for filter_key, value in params.items():
        if 'featured' == filter_key:
            #Support for 'featured=true' and 'featured=false'
            featured = value.lower() == "true"
            if featured:
                applications = [a for a in applications if a.featured()]
            else:
                applications = [a for a in applications if not a.featured()]
        elif 'bookmark' == filter_key:
            if type(user) == AnonymousUser:
                return []
            bookmarked_apps = [bm.application for bm in user.bookmarks.all()]
            applications = [a for a in applications if a in bookmarked_apps]
    return applications



class ApplicationList(APIView):
    """
        When this endpoint is called without authentication,
        a list of 'public' images is returned.
        When the endpoint is called with authentication,
        that list will include any private images the
        user is authorized to see.

        Applications are a set of one or more images that can
        be uniquely identified by a specific UUID, or more commonly, by Name,
        Description, or Tag(s).
    """

    permission_classes = (InMaintenance, ApiAuthOptional)

    def get(self, request, **kwargs):
        """Authentication optional, list of applications."""
        applications = public_applications()
        #Concatenate 'visible'
        if request.user and type(request.user) != AnonymousUser:
            my_apps = visible_applications(request.user)
            applications.extend(my_apps)
        params = request.QUERY_PARAMS
        applications = _filter_applications(applications, request.user, params)

        page = params.get('page')
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
            context={'request': request}).data
        response = Response(serialized_data)
        response['Cache-Control'] = 'no-cache'
        return response


class ApplicationThresholdDetail(APIView):
    """
        Applications are a set of one or more images that can
        be uniquely identified by a specific UUID, or more commonly, by Name,
        Description, or Tag(s).
    """

    permission_classes = (ApiAuthOptional,)

    def get(self, request, app_uuid, **kwargs):
        """
        Details of specific application's Threshold.
        Params:app_uuid -- Unique ID of Application

        """
        app = CoreApplication.objects.filter(uuid=app_uuid)
        if not app:
            return failure_response(status.HTTP_404_NOT_FOUND,
                                    "Application with uuid %s does not exist"
                                    % app_uuid)
        app = app[0]
        serialized_data = ApplicationThresholdSerializer(
            app.get_threshold(), context={'request': request}).data
        response = Response(serialized_data)
        return response

    def put(self, request, app_uuid, **kwargs):
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
        return self._update_threshold(request, app, **kwargs)

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
        return self._update_threshold(request, app, **kwargs)

    def delete(self, request, app_uuid, **kwargs):
        app = CoreApplication.objects.filter(uuid=app_uuid)
        if not app:
            return failure_response(status.HTTP_404_NOT_FOUND,
                                    "Application with uuid %s does not exist"
                                    % app_uuid)
        app = app[0]
        kwargs['delete'] = True
        return self._update_threshold(request, app, **kwargs)

    def _update_threshold(self, request, app, **kwargs):
        user = request.user
        data = request.DATA
        app_owner = app.created_by
        app_members = app.get_members()
        if user != app_owner and not Group.check_membership(user, app_members):
            return failure_response(status.HTTP_403_FORBIDDEN,
                                    "You are not the Application owner. "
                                    "This incident will be reported")
            #Or it wont.. Up to operations..
        if kwargs.get('delete'):
            threshold = app.get_threshold()
            if threshold:
                threshold.delete()
            serializer = ApplicationThresholdSerializer(
                app.get_threshold())
            return Response(serializer.data)
        partial_update = True if request.method == 'PATCH' else False
        serializer = ApplicationThresholdSerializer(
            app.threshold, data=data, context={'request': request},
            partial=partial_update)
        if serializer.is_valid():
            serializer.save()
            logger.info(serializer.data)
            return Response(serializer.data)
        return failure_response(
            status.HTTP_400_BAD_REQUEST,
            serializer.errors)


class Application(APIView):
    """
        Applications are a set of one or more images that can
        be uniquely identified by a specific UUID, or more commonly, by Name,
        Description, or Tag(s).
    """

    permission_classes = (ApiAuthOptional,)

    def get(self, request, app_uuid, **kwargs):
        """
        Details of specific application's Threshold.
        Params:app_uuid -- Unique ID of Application

        """
        app = CoreApplication.objects.filter(uuid=app_uuid)
        if not app:
            return failure_response(status.HTTP_404_NOT_FOUND,
                                    "Application with uuid %s does not exist"
                                    % app_uuid)
        app = app[0]
        serialized_data = ApplicationSerializer(
            app, context={'request': request}).data
        response = Response(serialized_data)
        return response

    def put(self, request, app_uuid, **kwargs):
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
        data = request.DATA
        app_owner = app.created_by
        app_members = app.get_members()
        if user != app_owner and not Group.check_membership(user, app_members):
            return failure_response(status.HTTP_403_FORBIDDEN,
                                    "You are not the Application owner. "
                                    "This incident will be reported")
            #Or it wont.. Up to operations..
        partial_update = True if request.method == 'PATCH' else False
        serializer = ApplicationSerializer(app, data=data,
                                           context={'request': request},
                                           partial=partial_update)
        if serializer.is_valid():
            logger.info('metadata = %s' % data)
            #TODO: Update application metadata on each machine?
            #update_machine_metadata(esh_driver, esh_machine, data)
            serializer.save()
            if 'created_by_identity' in request.DATA:
                identity = serializer.object.created_by_identity
                update_application_owner(serializer.object, identity)
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

    permission_classes = (InMaintenance, ApiAuthOptional)

    def get(self, request):
        """"""
        query = request.QUERY_PARAMS.get('query')
        if not query:
            return failure_response(
                status.HTTP_400_BAD_REQUEST,
                "Query not provided.")

        identity_uuid = request.QUERY_PARAMS.get('identity')
        identity = Identity.objects.filter(uuid=identity_uuid)
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
            context={'request': request}).data
        response = Response(serialized_data)
        response['Cache-Control'] = 'no-cache'
        return response
