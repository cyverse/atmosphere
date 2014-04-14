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

from authentication.decorators import api_auth_token_required

from api.serializers import ProjectSerializer, InstanceSerializer,\
        VolumeSerializer, ApplicationSerializer
from core.models.group import get_user_group

class ProjectApplicationExchange(APIView):
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

    @api_auth_token_required
    def get(self, request, project_id):
        """
        """
        user = request.user
        group = get_user_group(user.username)
        #TODO: Check that you have permission!
        projects = group.projects.get(id=project_id)
        volumes = projects.volumes.all()
        serialized_data = VolumeSerializer(volumes, many=True,
                                            context={"user":request.user}).data
        response = Response(serialized_data)
        return response

class ProjectApplicationList(APIView):
    """
    """

    @api_auth_token_required
    def get(self, request, project_id):
        """
        """
        user = request.user
        group = get_user_group(user.username)
        #TODO: Check that you have permission!
        projects = group.projects.get(id=project_id)
        applications = projects.applications.all()
        serialized_data = ApplicationSerializer(applications, many=True,
                                            context={"user":request.user}).data
        response = Response(serialized_data)
        return response

class ProjectInstanceList(APIView):
    """
    """

    @api_auth_token_required
    def get(self, request, project_id):
        """
        """
        user = request.user
        group = get_user_group(user.username)
        #TODO: Check that you have permission!
        projects = group.projects.get(id=project_id)
        instances = projects.instances.all()
        serialized_data = InstanceSerializer(instances, many=True,
                                            context={"user":request.user}).data
        response = Response(serialized_data)
        return response

class ProjectList(APIView):
    """
    """

    @api_auth_token_required
    def post(self, request):
        """
        """
        user = request.user
        data = request.DATA
        if data.get('name') == 'Default':
            return Response("The 'Default' project name is reserved",
                            status=status.HTTP_409_CONFLICT)
        serializer = ProjectSerializer(data=data,
                                            context={"user":request.user})
        if serializer.is_valid():
            serializer.save()
            response = Response(
                    serializer.data,
                    status=status.HTTP_201_CREATED)
            return response
        else:
            return Response(serializer.errors,
                    status=status.HTTP_400_BAD_REQUEST)

    @api_auth_token_required
    def get(self, request):
        """
        """
        user = request.user
        group = get_user_group(user.username)
        projects = group.projects.all()
        serialized_data = ProjectSerializer(projects, many=True,
                                            context={"user":request.user}).data
        response = Response(serialized_data)
        return response


class ProjectDetail(APIView):
    """
    """

    @api_auth_token_required
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
                                            context={"user":request.user})
        if serializer.is_valid():
            #If the default project was renamed
            if project.name == "Default" \
                    and serializer.object.name != "Default":
                #Create another one.
                group.projects.get_or_create(name="Default")
            serializer.save()
            response = Response(
                    serializer.data,
                    status=status.HTTP_201_CREATED)
            return response
        else:
            return Response(serializer.errors,
                    status=status.HTTP_400_BAD_REQUEST)

    @api_auth_token_required
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
                                            context={"user":request.user})
        if serializer.is_valid():
            #If the default project was renamed
            if project.name == "Default" \
                    and serializer.object.name != "Default":
                #Create another one.
                group.projects.get_or_create(name="Default")
            serializer.save()
            response = Response(
                    serializer.data,
                    status=status.HTTP_201_CREATED)
            return response
        else:
            return Response(serializer.errors,
                    status=status.HTTP_400_BAD_REQUEST)

    @api_auth_token_required
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
                                            context={"user":request.user}).data
        response = Response(serialized_data)
        return response


    @api_auth_token_required
    def delete(self, request, project_id):
        """
        """
        user = request.user
        group = get_user_group(user.username)
        project = group.projects.filter(id=project_id)
        if not project:
            return Response("Project with ID=%s does not exist" % project_id,
                            status=status.HTTP_400_BAD_REQUEST)
        if project.name == 'Default':
            return Response(
                    "The 'Default' project is reserved and cannot be deleted.",
                    status=status.HTTP_409_CONFLICT)
        project = project[0]
        default_project = group.projects.get(name='Default')
        project.migrate_objects(default_project)
        project.delete_project()
        serialized_data = ProjectSerializer(project,
                                            context={"user":request.user}).data
        response = Response(serialized_data)
        return response


