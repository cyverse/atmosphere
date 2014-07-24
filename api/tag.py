"""
Atmosphere service tag rest api.

"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status


from core.models import Tag as CoreTag
from api import failure_response
from api.serializers import TagSerializer
from api.permissions import InMaintenance, ApiAuthRequired, ApiAuthOptional


class TagList(APIView):
    """
        Tags are a easy way to allow users to group several images as similar
        based on a feature/program of the application.
    """
    permission_classes = (ApiAuthOptional,)
    
    def get(self, request, *args, **kwargs):
        """
        List all public tags.
        """
        tags = CoreTag.objects.all()
        serializer = TagSerializer(tags, many=True)
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        """Create a new tag resource
        Params:name -- Name of the new Tag
        Returns: 
        Status Code: 201 Body: A new Tag object
        Status Code: 400 Body: Errors (Duplicate/Invalid Name)
        """
        user = request.user
        data = request.DATA.copy()
        same_name_tags = CoreTag.objects.filter(name__iexact=data['name'])
        if same_name_tags:
            return Response(['A tag with this name already exists: %s'
                             % same_name_tags],
                            status=status.HTTP_400_BAD_REQUEST)
        data['user'] = user.username
        data['name'] = data['name'].lower()
        serializer = TagSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class Tag(APIView):
    """
        Tags are a easy way to allow users to group several images as similar
        based on a feature/program of the application.

        This API resource allows you to Retrieve, Update, or Delete your Tag.
    """
    permission_classes = (ApiAuthRequired,)
    
    def delete(self, request, tag_slug, *args, **kwargs):
        """
        Remove the tag, if it is no longer in use.
        """
        try:
            tag = CoreTag.objects.get(name__iexact=tag_slug)
        except CoreTag.DoesNotExist:
            return failure_response(status.HTTP_404_NOT_FOUND, 
                                    'Tag %s does not exist' % tag_slug)
        if tag.in_use():
            instance_count = tag.instance_set.count()
            app_count = tag.application_set.count()
            return failure_response(
                    status.HTTP_409_CONFLICT,                    
                    "Tag cannot be deleted while it is in use by"
                             "%s instances and %s applications. "
                             "To delete the tag, first remove "
                             "the tag from ALL objects using it"
                             % (instance_count, app_count))
        tag.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def get(self, request, tag_slug, *args, **kwargs):
        """
        Return the credential information for this tag
        """
        try:
            tag = CoreTag.objects.get(name__iexact=tag_slug)
        except CoreTag.DoesNotExist:
            return Response(['Tag does not exist'],
                            status=status.HTTP_404_NOT_FOUND)
        serializer = TagSerializer(tag)
        return Response(serializer.data)

    def put(self, request, tag_slug, *args, **kwargs):
        """
        Return the credential information for this tag
        """
        user = request.user
        tag = CoreTag.objects.get(name__iexact=tag_slug)
        if not user.is_staff and user != tag.user:
            return Response([
                'Only the tag creator can update a tag.'
                + 'Contact support if you need to change '
                + 'a tag that is not yours.'],
                status=status.HTTP_400_BAD_REQUEST)
        #Allowed to update tags..
        data = request.DATA.copy()
        if tag.user:
            data['user'] = tag.user.id
        else:
            data['user'] = user.id

        # Tag names are immutable
        data['name'] = tag.name
        serializer = TagSerializer(tag, data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
