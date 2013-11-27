"""
Atmosphere service volume
"""

from datetime import datetime

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from threepio import logger

from authentication.decorators import api_auth_token_required

from core.models.provider import AccountProvider
from core.models.volume import convert_esh_volume
from core.models.quota import\
    Quota as CoreQuota, get_quota, has_storage_quota, has_storage_count_quota

from api.serializers import VolumeSerializer

from api import prepare_driver, failureJSON


class VolumeList(APIView):
    """
    List all volumes
    """
    @api_auth_token_required
    def get(self, request, provider_id, identity_id):
        """
        Retrieves list of volumes and updates the DB
        """
        user = request.user
        esh_driver = prepare_driver(request, identity_id)
        volume_list_method = esh_driver.list_volumes

        if AccountProvider.objects.filter(identity__id=identity_id):
            # Instance list method changes when using the OPENSTACK provider
            volume_list_method = esh_driver.list_all_volumes

        esh_volume_list = volume_list_method()

        core_volume_list = [convert_esh_volume(volume, provider_id, identity_id, user)
                            for volume in esh_volume_list]
        serializer = VolumeSerializer(core_volume_list, many=True)
        response = Response(serializer.data)
        return response

    @api_auth_token_required
    def post(self, request, provider_id, identity_id):
        """
        Creates a new volume and adds it to the DB
        """
        user = request.user
        esh_driver = prepare_driver(request, identity_id)
        data = request.DATA
        if not data.get('name') or not data.get('size'):
            errorObj = failureJSON([{
                'code': 400,
                'message':
                'Missing params: name and size required to create a volume'}])
            return Response(errorObj, status=status.HTTP_400_BAD_REQUEST)
        name = data.get('name')
        size = data.get('size')
        quota = get_quota(identity_id)
        CoreQuota.objects.get(identitymembership__identity__id=identity_id)

        if not has_storage_quota(esh_driver, quota, size) \
                or not has_storage_count_quota(esh_driver, quota, 1):
            errorObj = failureJSON([{
                'code': 403,
                'message':
                'Over quota: '
                + 'You have used all of your allocated volume quota'}])
            return Response(errorObj, status=status.HTTP_403_FORBIDDEN)

        logger.debug((name, size))
        success, esh_volume = esh_driver.create_volume(
            name=name,
            size=size,
            description=data.get('description', ''))
        if not success:
            errorObj = failureJSON({'code': 500,
                                    'message': 'Volume creation failed'})
            return Response(errorObj,
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        core_volume = convert_esh_volume(esh_volume, provider_id, identity_id, user)
        serialized_data = VolumeSerializer(core_volume).data
        response = Response(serialized_data, status=status.HTTP_201_CREATED)
        return response


class Volume(APIView):
    """
    List all volumes
    """
    @api_auth_token_required
    def get(self, request, provider_id, identity_id, volume_id):
        """
        """
        user = request.user
        esh_driver = prepare_driver(request, identity_id)
        esh_volume = esh_driver.get_volume(volume_id)
        if not esh_volume:
            errorObj = failureJSON([{'code': 404,
                                    'message': 'Volume does not exist'}])
            return Response(errorObj, status=status.HTTP_404_NOT_FOUND)
        core_volume = convert_esh_volume(esh_volume, provider_id, identity_id, user)
        serialized_data = VolumeSerializer(core_volume).data
        response = Response(serialized_data)
        return response

    @api_auth_token_required
    def patch(self, request, provider_id, identity_id, volume_id):
        """
        Updates DB values for volume
        """
        user = request.user
        data = request.DATA
        #Ensure volume exists
        esh_driver = prepare_driver(request, identity_id)
        esh_volume = esh_driver.get_volume(volume_id)
        if not esh_volume:
            errorObj = failureJSON([{'code': 404,
                                     'message': 'Volume does not exist'}])
            return Response(errorObj, status=status.HTTP_404_NOT_FOUND)
        core_volume = convert_esh_volume(esh_volume, provider_id, identity_id, user)
        serializer = VolumeSerializer(core_volume, data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            response = Response(serializer.data)
            return response
        else:
            return Response(serializer.errors, status=400)

    @api_auth_token_required
    def put(self, request, provider_id, identity_id, volume_id):
        """
        Updates DB values for volume
        """
        user = request.user
        data = request.DATA
        #Ensure volume exists
        esh_driver = prepare_driver(request, identity_id)
        esh_volume = esh_driver.get_volume(volume_id)
        if not esh_volume:
            errorObj = failureJSON([{'code': 404,
                                     'message': 'Volume does not exist'}])
            return Response(errorObj, status=status.HTTP_404_NOT_FOUND)
        core_volume = convert_esh_volume(esh_volume, provider_id, identity_id, user)
        serializer = VolumeSerializer(core_volume, data=data)
        if serializer.is_valid():
            serializer.save()
            response = Response(serializer.data)
            return response
        else:
            return Response(serializer.errors, status=400)

    @api_auth_token_required
    def delete(self, request, provider_id, identity_id, volume_id):
        """
        Destroys the volume and updates the DB
        """
        user = request.user
        #Ensure volume exists
        esh_driver = prepare_driver(request, identity_id)
        esh_volume = esh_driver.get_volume(volume_id)
        if not esh_volume:
            errorObj = failureJSON([{'code': 404,
                                     'message': 'Volume does not exist'}])
            return Response(errorObj, status=status.HTTP_404_NOT_FOUND)
        core_volume = convert_esh_volume(esh_volume, provider_id, identity_id, user)
        #Delete the object, update the DB
        esh_driver.destroy_volume(esh_volume)
        core_volume.end_date = datetime.now()
        core_volume.save()
        #Return the object
        serialized_data = VolumeSerializer(core_volume).data
        response = Response(serialized_data)
        return response
