"""
Atmosphere service instance rest api.

"""
## Frameworks
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.reverse import reverse

from threepio import logger
## Atmosphere Libraries

from authentication.decorators import api_auth_token_required

from api.serializers import ProjectSerializer

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
        projects = user.projects.all()
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
        project = user.projects.filter(id=project_id)
        if not project:
            return Response("Project with ID=%s does not exist" % project_id,
                            status=status.HTTP_404_BAD_REQUEST)
        project = project[0]
        serializer = ProjectSerializer(project, data=data, partial=True,
                                            context={"user":request.user})
        if serializer.is_valid():
            #If the default project was renamed
            if project.name == "Default" \
                    and serializer.object.name != "Default":
                #Create another one.
                user.projects.get_or_create(name="Default")
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
        project = user.projects.filter(id=project_id)
        if not project:
            return Response("Project with ID=%s does not exist" % project_id,
                            status=status.HTTP_404_BAD_REQUEST)
        project = project[0]
        serializer = ProjectSerializer(project, data=data,
                                            context={"user":request.user})
        if serializer.is_valid():
            #If the default project was renamed
            if project.name == "Default" \
                    and serializer.object.name != "Default":
                #Create another one.
                user.projects.get_or_create(name="Default")
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
        project = user.projects.filter(id=project_id)
        if not project:
            return Response("Project with ID=%s does not exist" % project_id,
                            status=status.HTTP_404_BAD_REQUEST)
        serialized_data = ProjectSerializer(project,
                                            context={"user":request.user}).data
        response = Response(serialized_data)
        return response


    @api_auth_token_required
    def delete(self, request, project_id):
        """
        """
        user = request.user
        project = user.projects.filter(id=project_id)
        if not project:
            return Response("Project with ID=%s does not exist" % project_id,
                            status=status.HTTP_404_BAD_REQUEST)
        if project.name == 'Default':
            return Response(
                    "The 'Default' project is reserved and cannot be deleted.",
                    status=status.HTTP_409_CONFLICT)
        project = project[0]
        default_project = user.projects.get(name='Default')
        project.migrate_objects(default_project)
        project.delete_project()
        serialized_data = ProjectSerializer(project,
                                            context={"user":request.user}).data
        response = Response(serialized_data)
        return response


