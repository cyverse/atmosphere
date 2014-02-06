"""
Atmosphere service volume
"""

from django.utils.timezone import datetime

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from libcloud.common.types import InvalidCredsError

from threepio import logger

from authentication.decorators import api_auth_token_required

from core.models.provider import AccountProvider
from core.models.volume import convert_esh_volume
from service.volume import create_volume
from service.exceptions import OverQuotaError

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
        missing_keys = valid_post_data(data)
        if missing_keys:
            return keys_not_found(missing_keys)
        #Pass arguments
        name = data.get('name')
        size = data.get('size')
        description = data.get('description')
        try:
            success, esh_volume = create_volume(esh_driver, identity_id,
                                                name, size, description)
        except OverQuotaError, oqe:
            return over_quota(oqe)
        except InvalidCredsError:
            return invalid_creds(provider_id, identity_id)
        if not success:
            errorObj = failureJSON(
                    {'code': 500,
                     'message': 'Volume creation failed. Contact support'})
            return Response(errorObj,
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        # Volume creation succeeded
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
            return volume_not_found(volume_id)
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
            return volume_not_found(volume_id)
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
            return volume_not_found(volume_id)
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
            return volume_not_found(volume_id)
        core_volume = convert_esh_volume(esh_volume, provider_id, identity_id, user)
        #Delete the object, update the DB
        esh_driver.destroy_volume(esh_volume)
        core_volume.end_date = datetime.now()
        core_volume.save()
        #Return the object
        serialized_data = VolumeSerializer(core_volume).data
        response = Response(serialized_data)
        return response

# Commonly used error responses
def valid_post_data(data):
    expected_data = ['name','size']
    missing_keys = []
    for key in expected_data:
        if not data.has_key(key):
            missing_keys.append(key)
    return missing_keys


def keys_not_found(missing_keys):
    errorObj = failureJSON([{
        'code': 400,
        'message': 'Missing required POST datavariables : %s' % missing_keys}])
    return Response(errorObj, status=status.HTTP_400_BAD_REQUEST)


def invalid_creds(provider_id, identity_id):
    logger.warn('Authentication Failed. Provider-id:%s Identity-id:%s'
                % (provider_id, identity_id))
    errorObj = failureJSON([{'code': 401,
        'message': 'Identity/Provider Authentication Failed'}])
    return Response(errorObj, status=status.HTTP_400_BAD_REQUEST)


def volume_not_found(volume_id):
    errorObj = failureJSON([{
        'code': 404,
        'message': 'Volume %s does not exist' % volume_id}])
    return Response(errorObj, status=status.HTTP_404_NOT_FOUND)


def over_quota(quota_exception):
    errorObj = failureJSON([{
        'code': 413,
        'message': quota_exception.message}])
    return Response(errorObj, status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)
