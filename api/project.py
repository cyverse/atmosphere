"""
Atmosphere service instance rest api.

"""
## Frameworks
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.reverse import reverse

from threepio import logger
## Atmosphere Libraries


from api import failure_response
from api.serializers import ProjectSerializer, InstanceSerializer,\
        VolumeSerializer, ApplicationSerializer
from core.models.group import Group, get_user_group
from api.permissions import InMaintenance, ApiAuthRequired
from api.serializers import NoProjectSerializer

from django.utils import timezone
from django.db.models import Q


def only_active():
    """
    Returns a query to filter only active Django ORM objects.

    NOTE: This needs to be a function because otherwise timezone.now() is
    evaluated when the module is evaluated and the logic does't work
    appropriately.
    """
    return Q(end_date=None) | Q(end_date__gt=timezone.now())


class ProjectApplicationExchange(APIView):
    permission_classes = (ApiAuthRequired,)
    def put(self, request, project_id, application_uuid):
        user = request.user
        group = get_user_group(user.username)
        project = group.projects.filter(id=project_id)
        if not project:
            return Response("Project with ID=%s does not exist" % project_id,
                            status=status.HTTP_400_BAD_REQUEST)
        project = project[0]
        application = user.application_set.filter(uuid=application_uuid)
        if not application:
            return Response("application with ID=%s not found in the database"
                            % (application_uuid,),
                            status=status.HTTP_400_BAD_REQUEST)
        application = application[0]
        project.add_object(application)
        response = Response(status=status.HTTP_204_NO_CONTENT)
        return response

    def delete(self, request, project_id, application_uuid):
        user = request.user
        group = get_user_group(user.username)
        project = group.projects.filter(id=project_id)
        if not project:
            return Response("Project with ID=%s does not exist" % project_id,
                            status=status.HTTP_400_BAD_REQUEST)
        project = project[0]
        application = project.applications.filter(provider_alias=application_uuid)
        if not application:
            error_str = "application with ID=%s does not exist in Project %s"\
                        % (application_uuid, project.id),
            return Response(error_str, status=status.HTTP_400_BAD_REQUEST)
        application = application[0]
        project.remove_object(application)
        response = Response(status=status.HTTP_204_NO_CONTENT)
        return response


class ProjectInstanceExchange(APIView):
    permission_classes = (ApiAuthRequired,)
    def put(self, request, project_id, instance_id):
        user = request.user
        group = get_user_group(user.username)
        project = group.projects.filter(id=project_id)
        if not project:
            return Response("Project with ID=%s does not exist" % project_id,
                            status=status.HTTP_400_BAD_REQUEST)
        project = project[0]
        instance = user.instance_set.filter(provider_alias=instance_id)
        if not instance:
            return Response("instance with ID=%s not found in the database"
                            % (instance_id,),
                            status=status.HTTP_400_BAD_REQUEST)
        instance = instance[0]
        existing_projects = instance.project_set.all()
        if existing_projects:
            for proj in existing_projects:
                proj.remove_object(instance)

        project.add_object(instance)
        response = Response(status=status.HTTP_204_NO_CONTENT)
        return response

    def delete(self, request, project_id, instance_id):
        user = request.user
        group = get_user_group(user.username)
        project = group.projects.filter(id=project_id)
        if not project:
            return Response("Project with ID=%s does not exist" % project_id,
                            status=status.HTTP_400_BAD_REQUEST)
        project = project[0]
        instance = project.instances.filter(provider_alias=instance_id)
        if not instance:
            error_str = "instance with ID=%s does not exist in Project %s"\
                        % (instance_id, project.id),
            return Response(error_str, status=status.HTTP_400_BAD_REQUEST)
        instance = instance[0]
        project.remove_object(instance)
        response = Response(status=status.HTTP_204_NO_CONTENT)
        return response


class ProjectVolumeExchange(APIView):
    permission_classes = (ApiAuthRequired,)
    def put(self, request, project_id, volume_id):
        user = request.user
        group = get_user_group(user.username)
        project = group.projects.filter(id=project_id)
        if not project:
            return Response("Project with ID=%s does not exist" % project_id,
                            status=status.HTTP_400_BAD_REQUEST)
        project = project[0]
        volume = user.volume_set.filter(alias=volume_id)
        if not volume:
            return Response("volume with ID=%s not found in the database"
                            % (volume_id,),
                            status=status.HTTP_400_BAD_REQUEST)
        volume = volume[0]
        existing_projects = volume.project_set.all()
        if existing_projects:
            for proj in existing_projects:
                proj.remove_object(volume)

        project.add_object(volume)
        response = Response(status=status.HTTP_204_NO_CONTENT)
        return response

    def delete(self, request, project_id, volume_id):
        user = request.user
        group = get_user_group(user.username)
        project = group.projects.filter(id=project_id)
        if not project:
            return Response("Project with ID=%s does not exist" % project_id,
                            status=status.HTTP_400_BAD_REQUEST)
        project = project[0]
        volume = project.volumes.filter(alias=volume_id)
        if not volume:
            error_str = "volume with ID=%s does not exist in Project %s"\
                        % (volume_id, project.id),
            return Response(error_str, status=status.HTTP_400_BAD_REQUEST)
        volume = volume[0]
        project.remove_object(volume)
        response = Response(status=status.HTTP_204_NO_CONTENT)
        return response

class ProjectVolumeList(APIView):
    """
    """
    permission_classes = (ApiAuthRequired,)

    def get(self, request, project_id):
        """
        """
        user = request.user
        group = get_user_group(user.username)
        #TODO: Check that you have permission!
        projects = group.projects.get(id=project_id)
        volumes = projects.volumes.filter(only_active())
        serialized_data = VolumeSerializer(volumes, many=True,
                                            context={"request":request}).data
        response = Response(serialized_data)
        return response

class ProjectApplicationList(APIView):
    """
    """
    permission_classes = (ApiAuthRequired,)

    def get(self, request, project_id):
        """
        """
        user = request.user
        group = get_user_group(user.username)
        #TODO: Check that you have permission!
        projects = group.projects.get(id=project_id)
        applications = projects.applications.filter(only_active())
        serialized_data = ApplicationSerializer(applications, many=True,
                                                context={"request":request}).data
        response = Response(serialized_data)
        return response

class ProjectInstanceList(APIView):
    """
    """

    permission_classes = (ApiAuthRequired,)

    def get(self, request, project_id):
        """
        """
        user = request.user
        group = get_user_group(user.username)
        #TODO: Check that you have permission!
        projects = group.projects.get(id=project_id)
        instances = projects.instances.filter(only_active())
        serialized_data = InstanceSerializer(instances, many=True,
                                            context={"request":request}).data
        response = Response(serialized_data)
        return response

class NoProjectList(APIView):
    """
    """

    permission_classes = (ApiAuthRequired,)
    def get(self, request):
        """
        """
        user = request.user
        #Get all instances, volumes, applications owned by me
        #where project==None
        serialized_data = NoProjectSerializer(user,
                                            context={"request":request}).data
        response = Response(serialized_data)
        return response

class ProjectList(APIView):
    """
    """

    permission_classes = (ApiAuthRequired,)

    def post(self, request):
        """
        """
        user = request.user
        data = request.DATA
        #Default to creating for the 'user-group'
        if not data.get('owner'):
            data['owner'] = user.username
        elif not Group.check_access(user, data['owner']):
            return failure_response(
                    status.HTTP_403_FORBIDDEN,
                    "Current User: %s - Cannot assign project for group %s"
                    % (user.username, data['owner']))
        serializer = ProjectSerializer(data=data,
                                       context={"request":request})
        if serializer.is_valid():
            serializer.save()
            response = Response(
                    serializer.data,
                    status=status.HTTP_201_CREATED)
            return response
        else:
            return Response(serializer.errors,
                    status=status.HTTP_400_BAD_REQUEST)

    def get(self, request):
        """
        """
        user = request.user
        group = get_user_group(user.username)
        projects = group.projects.filter(Q(end_date=None) | Q(end_date__gt=timezone.now()))
        serialized_data = ProjectSerializer(projects, many=True,
                                            context={"request":request}).data
        response = Response(serialized_data)
        return response


class ProjectDetail(APIView):
    """
    """

    permission_classes = (ApiAuthRequired,)

    def patch(self, request, project_id):
        """
        """
        user = request.user
        data = request.DATA
        group = get_user_group(user.username)
        project = group.projects.filter(id=project_id)
        if not project:
            return Response("Project with ID=%s does not exist" % project_id,
                            status=status.HTTP_400_BAD_REQUEST)
        project = project[0]
        serializer = ProjectSerializer(project, data=data, partial=True,
                                            context={"request":request})
        if serializer.is_valid():
            serializer.save()
            response = Response(
                    serializer.data,
                    status=status.HTTP_201_CREATED)
            return response
        else:
            return Response(serializer.errors,
                    status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, project_id):
        """
        """
        user = request.user
        data = request.DATA
        group = get_user_group(user.username)
        project = group.projects.filter(id=project_id)
        if not project:
            return Response("Project with ID=%s does not exist" % project_id,
                            status=status.HTTP_400_BAD_REQUEST)
        project = project[0]
        serializer = ProjectSerializer(project, data=data,
                                            context={"request":request})
        if serializer.is_valid():
            serializer.save()
            response = Response(
                    serializer.data,
                    status=status.HTTP_201_CREATED)
            return response
        else:
            return Response(serializer.errors,
                    status=status.HTTP_400_BAD_REQUEST)

    def get(self, request, project_id):
        """
        """
        user = request.user
        group = get_user_group(user.username)
        project = group.projects.filter(id=project_id)
        if not project:
            return Response("Project with ID=%s does not exist" % project_id,
                            status=status.HTTP_400_BAD_REQUEST)
        serialized_data = ProjectSerializer(project,
                                            context={"request":request}).data
        response = Response(serialized_data)
        return response


    def delete(self, request, project_id):
        """
        """
        user = request.user
        group = get_user_group(user.username)
        project = group.projects.filter(id=project_id)
        if not project:
            return Response("Project with ID=%s does not exist" % project_id,
                            status=status.HTTP_400_BAD_REQUEST)
        project = project[0]
        if project.has_resources():
            return Response(
                "Project with ID=%s has running resources. "
                "Resources MUST be deleted before deleting the project."
                % project_id, status=status.HTTP_409_CONFLICT)
        project.delete_project()
        serialized_data = ProjectSerializer(project,
                                            context={"request":request}).data
        response = Response(serialized_data)
        return response


