"""
Atmosphere service volume
"""

from datetime import datetime

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from atmosphere.logger import logger

from authentication.decorators import api_auth_token_required

from core.models.quota import\
    getQuota, Quota as CoreQuota, storageQuotaTest, storageCountQuotaTest
from core.models.volume import convertEshVolume

from service.api.serializers import VolumeSerializer

from service.api import prepareDriver, failureJSON


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
        esh_driver = prepareDriver(request, identity_id)
        esh_volume_list = esh_driver.list_volumes()
        core_volume_list = [convertEshVolume(volume, provider_id, user)
                            for volume in esh_volume_list]
        serializer = VolumeSerializer(core_volume_list)
        response = Response(serializer.data)
        return response

    @api_auth_token_required
    def post(self, request, provider_id, identity_id):
        """
        Creates a new volume and adds it to the DB
        """
        user = request.user
        esh_driver = prepareDriver(request, identity_id)
        data = request.DATA
        if not data.get('name') or not data.get('size'):
            errorObj = failureJSON([{
                'code': 400,
                'message':
                'Missing params: name and size required to create a volume'}])
            return Response(errorObj, status=status.HTTP_400_BAD_REQUEST)
        name = data.get('name')
        size = data.get('size')
        quota = getQuota(identity_id)
        CoreQuota.objects.get(identitymembership__identity__id=identity_id)

        if not storageQuotaTest(esh_driver, quota, size) \
                or not storageCountQuotaTest(esh_driver, quota, 1):
            errorObj = failureJSON([{
                'code': 403,
                'message':
                'Over quota: '
                + 'You have used all of your allocated volume quota'}])
            return Response(errorObj, status=status.HTTP_403_FORBIDDEN)

        logger.debug((name, size))
        success, eshVolume = esh_driver.create_volume(
            name=name,
            size=size,
            description=data.get('description', ''))
        if not success:
            errorObj = failureJSON({'code': 500,
                                    'message': 'Volume creation failed'})
            return Response(errorObj,
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        coreVolume = convertEshVolume(eshVolume, provider_id, user)
        serialized_data = VolumeSerializer(coreVolume).data
        response = Response(serialized_data)
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
        esh_driver = prepareDriver(request, identity_id)
        eshVolume = esh_driver.get_volume(volume_id)
        if not eshVolume:
            errorObj = failureJSON([{'code': 404,
                                    'message': 'Volume does not exist'}])
            return Response(errorObj, status=status.HTTP_404_NOT_FOUND)
        coreVolume = convertEshVolume(eshVolume, provider_id, user)
        serialized_data = VolumeSerializer(coreVolume).data
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
        esh_driver = prepareDriver(request, identity_id)
        eshVolume = esh_driver.get_volume(volume_id)
        if not eshVolume:
            errorObj = failureJSON([{'code': 404,
                                     'message': 'Volume does not exist'}])
            return Response(errorObj, status=status.HTTP_404_NOT_FOUND)
        coreVolume = convertEshVolume(eshVolume, provider_id, user)
        serializer = VolumeSerializer(coreVolume, data=data, partial=True)
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
        esh_driver = prepareDriver(request, identity_id)
        eshVolume = esh_driver.get_volume(volume_id)
        if not eshVolume:
            errorObj = failureJSON([{'code': 404,
                                     'message': 'Volume does not exist'}])
            return Response(errorObj, status=status.HTTP_404_NOT_FOUND)
        coreVolume = convertEshVolume(eshVolume, provider_id, user)
        serializer = VolumeSerializer(coreVolume, data=data)
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
        esh_driver = prepareDriver(request, identity_id)
        eshVolume = esh_driver.get_volume(volume_id)
        if not eshVolume:
            errorObj = failureJSON([{'code': 404,
                                     'message': 'Volume does not exist'}])
            return Response(errorObj, status=status.HTTP_404_NOT_FOUND)
        coreVolume = convertEshVolume(eshVolume, provider_id, user)
        #Delete the object, update the DB
        esh_driver.destroy_volume(eshVolume)
        coreVolume.end_date = datetime.now()
        coreVolume.save()
        #Return the object
        serialized_data = VolumeSerializer(coreVolume).data
        response = Response(serialized_data)
        return response
