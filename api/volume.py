"""
Atmosphere service volume
"""
from django.utils.timezone import datetime

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from libcloud.common.types import InvalidCredsError

from threepio import logger


from core.models.provider import AccountProvider
from core.models.volume import convert_esh_volume

from service.volume import create_volume, boot_volume
from service.exceptions import OverQuotaError

from api import prepare_driver, failure_response, invalid_creds
from api.permissions import InMaintenance, ApiAuthRequired
from api.serializers import VolumeSerializer


class VolumeList(APIView):
    """List all volumes on Identity"""

    permission_classes = (ApiAuthRequired,)

    def get(self, request, provider_id, identity_id):
        """
        Retrieves list of volumes and updates the DB
        """
        user = request.user
        esh_driver = prepare_driver(request, provider_id, identity_id)
        if not esh_driver:
            return invalid_creds(provider_id, identity_id)
        volume_list_method = esh_driver.list_volumes

        if AccountProvider.objects.filter(identity__id=identity_id):
            # Instance list method changes when using the OPENSTACK provider
            volume_list_method = esh_driver.list_all_volumes

        esh_volume_list = volume_list_method()

        core_volume_list = [convert_esh_volume(volume, provider_id,
                                               identity_id, user)
                            for volume in esh_volume_list]
        serializer = VolumeSerializer(core_volume_list,
                                      context={'user':request.user}, many=True)
        response = Response(serializer.data)
        return response

    def post(self, request, provider_id, identity_id):
        """
        Creates a new volume and adds it to the DB
        """
        user = request.user
        esh_driver = prepare_driver(request, provider_id, identity_id)
        if not esh_driver:
            return invalid_creds(provider_id, identity_id)
        data = request.DATA
        missing_keys = valid_create_data(data)
        if missing_keys:
            return keys_not_found(missing_keys)
        #Pass arguments
        name = data.get('name')
        size = data.get('size')
        #Optional fields
        description = data.get('description')
        image_id = data.get('image')
        if image_id:
            image = driver.get_machine(image_id)
            image_size = image._connection.get_size(image._image)
            if int(size) > image_size + 4:
            return failure_response(
                status.HTTP_400_BAD_REQUEST,
                "Volumes created from images can be no more than 4GB larger "
                " than the size of the image: %s GB" % image_size)

        snapshot_id = data.get('snapshot')
        if snapshot_id:
            snapshot = driver._connection.ex_get_snapshot(image_id)
        try:
            success, esh_volume = create_volume(esh_driver, identity_id,
                                                name, size, description,
                                                snapshot=snapshot, image=image)
        except OverQuotaError, oqe:
            return over_quota(oqe)
        except InvalidCredsError:
            return invalid_creds(provider_id, identity_id)
        if not success:
            return failure_response(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                'Volume creation failed. Contact support')
        # Volume creation succeeded
        core_volume = convert_esh_volume(esh_volume, provider_id,
                                         identity_id, user)
        serialized_data = VolumeSerializer(core_volume,
                                           context={'user':request.user}).data
        return Response(serialized_data, status=status.HTTP_201_CREATED)


class Volume(APIView):
    """Details of specific volume on Identity."""
    permission_classes = (ApiAuthRequired,)
    
    def get(self, request, provider_id, identity_id, volume_id):
        """
        """
        user = request.user
        esh_driver = prepare_driver(request, provider_id, identity_id)
        if not esh_driver:
            return invalid_creds(provider_id, identity_id)
        esh_volume = esh_driver.get_volume(volume_id)
        if not esh_volume:
            return volume_not_found(volume_id)
        core_volume = convert_esh_volume(esh_volume, provider_id,
                                         identity_id, user)
        serialized_data = VolumeSerializer(core_volume,
                                           context={'user':request.user}).data
        response = Response(serialized_data)
        return response

    def patch(self, request, provider_id, identity_id, volume_id):
        """
        Updates DB values for volume
        """
        user = request.user
        data = request.DATA
        #Ensure volume exists
        esh_driver = prepare_driver(request, provider_id, identity_id)
        if not esh_driver:
            return invalid_creds(provider_id, identity_id)
        esh_volume = esh_driver.get_volume(volume_id)
        if not esh_volume:
            return volume_not_found(volume_id)
        core_volume = convert_esh_volume(esh_volume, provider_id,
                                         identity_id, user)
        serializer = VolumeSerializer(core_volume, data=data, 
                                      context={'user':request.user},
                
                partial=True)
        if serializer.is_valid():
            serializer.save()
            response = Response(serializer.data)
            return response
        else:
            return failure_response(
                status.HTTP_400_BAD_REQUEST,
                serializer.errors)

    def put(self, request, provider_id, identity_id, volume_id):
        """
        Updates DB values for volume
        """
        user = request.user
        data = request.DATA
        #Ensure volume exists
        esh_driver = prepare_driver(request, provider_id, identity_id)
        if not esh_driver:
            return invalid_creds(provider_id, identity_id)
        esh_volume = esh_driver.get_volume(volume_id)
        if not esh_volume:
            return volume_not_found(volume_id)
        core_volume = convert_esh_volume(esh_volume, provider_id,
                                         identity_id, user)
        serializer = VolumeSerializer(core_volume, data=data,
                                      context={'user':request.user},
                
                )
        if serializer.is_valid():
            serializer.save()
            response = Response(serializer.data)
            return response
        else:
            failure_response(
                status.HTTP_400_BAD_REQUEST,
                serializer.errors)

    def delete(self, request, provider_id, identity_id, volume_id):
        """
        Destroys the volume and updates the DB
        """
        user = request.user
        #Ensure volume exists
        esh_driver = prepare_driver(request, provider_id, identity_id)
        if not esh_driver:
            return invalid_creds(provider_id, identity_id)
        esh_volume = esh_driver.get_volume(volume_id)
        if not esh_volume:
            return volume_not_found(volume_id)
        core_volume = convert_esh_volume(esh_volume, provider_id,
                                         identity_id, user)
        #Delete the object, update the DB
        esh_driver.destroy_volume(esh_volume)
        core_volume.end_date = datetime.now()
        core_volume.save()
        #Return the object
        serialized_data = VolumeSerializer(core_volume,
                                           context={'user':request.user},
                
                ).data
        response = Response(serialized_data)
        return response


class BootVolume(APIView):
    """Launch an instance using this volume as the source"""
    permission_classes = (ApiAuthRequired,)
    
    def post(self, request, provider_id, identity_id, volume_id=None):
        user = request.user
        esh_driver = prepare_driver(request, provider_id, identity_id)
        data = request.DATA

        missing_keys = valid_launch_data(data)
        if missing_keys:
            return keys_not_found(missing_keys)
        if not esh_driver:
            return invalid_creds(provider_id, identity_id)
        name = data.pop('name')
        size = data.pop('size')
        image_id = data.pop('image_id',None)
        response, esh_volume = boot_volume(esh_driver, identity_id, name, size, image_id=image_id, volume_id=volume_id, **data)
        core_volume = convert_esh_volume(esh_volume, provider_id,
                                         identity_id, user)
        serialized_data = VolumeSerializer(core_volume,
                                           context={'user':request.user}).data
        response = Response(serialized_data)

def valid_launch_data(data):
    """
    Return any missing required post key names.
    """
    required = ['name', 'size']
    return [key for key in required
            #Key must exist and have a non-empty value.
            if not ( key in data and len(data[key]) > 0)]

def valid_create_data(data):
    """
    Return any missing required post key names.
    """
    required = ['name', 'size']
    return [key for key in required
            #Key must exist and have a non-empty value.
            if not ( key in data and len(data[key]) > 0)]


def keys_not_found(missing_keys):
    return failure_response(
        status.HTTP_400_BAD_REQUEST,
        'Missing required POST datavariables : %s' % missing_keys)


def volume_not_found(volume_id):
    return failure_response(
        status.HTTP_404_NOT_FOUND,
        'Volume %s does not exist' % volume_id)


def over_quota(quota_exception):
    return failure_response(
        status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        quota_exception.message)
