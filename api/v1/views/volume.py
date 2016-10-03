"""
Atmosphere service volume
"""
from socket import error as socket_error

from django.utils.timezone import datetime, now

from rest_framework.response import Response
from rest_framework import status

from rtwo.exceptions import ConnectionFailure
from rtwo.exceptions import LibcloudInvalidCredsError, LibcloudBadResponseError
from libcloud.common.exceptions import BaseHTTPError

from threepio import logger

from api.exceptions import failure_response, inactive_provider

from core.exceptions import ProviderNotActive
from core.models.provider import AccountProvider
from core.models.volume import convert_esh_volume
from core.models.volume import Volume as CoreVolume
from core.models.instance_source import InstanceSource
from core.models.group import IdentityMembership

from service.driver import prepare_driver
from service.volume import create_esh_volume,\
    create_bootable_volume,\
    _update_volume_metadata
from service.exceptions import OverQuotaError

from api import invalid_creds, connection_failure,\
    malformed_response
from api.v1.serializers import VolumeSerializer, InstanceSerializer
from api.v1.views.base import AuthAPIView


class VolumeSnapshot(AuthAPIView):

    """
    Initialize and view volume snapshots.
    """

    def get(self, request, provider_uuid, identity_uuid):
        """
        """
        try:
            esh_driver = prepare_driver(request, provider_uuid, identity_uuid)
        except ProviderNotActive as pna:
            return inactive_provider(pna)
        except Exception as e:
            return failure_response(
                status.HTTP_409_CONFLICT,
                e.message)
        if not esh_driver:
            return invalid_creds(provider_uuid, identity_uuid)
        try:
            esh_snapshots = esh_driver._connection.ex_list_snapshots()
        except LibcloudBadResponseError:
            return malformed_response(provider_uuid, identity_uuid)
        except LibcloudInvalidCredsError:
            return invalid_creds(provider_uuid, identity_uuid)
        snapshot_data = []
        for ss in esh_snapshots:
            snapshot_data.append({
                'id': ss.id,
                'name': ss.extra['name'],
                'size': ss.size,
                'description': ss.extra['description'],
                'created': ss.extra['created'],
                'status': ss.extra['status'],
                'volume_id': ss.extra['volume_id'], })

        response = Response(snapshot_data)
        return response

    def post(self, request, provider_uuid, identity_uuid):
        """
        Updates DB values for volume
        """
        user = request.user
        data = request.data

        missing_keys = valid_snapshot_post_data(data)
        if missing_keys:
            return keys_not_found(missing_keys)
        # Required
        size = data.get('size')
        volume_id = data.get('volume_id')
        display_name = data.get('display_name')
        # Optional
        description = data.get('description')
        metadata = data.get('metadata')
        snapshot_id = data.get('snapshot_id')
        # STEP 0 - Existence tests
        try:
            esh_driver = prepare_driver(request, provider_uuid, identity_uuid)
        except ProviderNotActive as pna:
            return inactive_provider(pna)
        except Exception as e:
            return failure_response(
                status.HTTP_409_CONFLICT,
                e.message)
        if not esh_driver:
            return invalid_creds(provider_uuid, identity_uuid)
        try:
            esh_volume = esh_driver.get_volume(volume_id)
        except (socket_error, ConnectionFailure):
            return connection_failure(provider_uuid, identity_uuid)
        except LibcloudInvalidCredsError:
            return invalid_creds(provider_uuid, identity_uuid)
        except Exception as exc:
            logger.exception("Encountered a generic exception. "
                             "Returning 409-CONFLICT")
            return failure_response(status.HTTP_409_CONFLICT,
                                    str(exc.message))
        # TODO: Put quota tests at the TOP so we dont over-create resources!
        # STEP 1 - Reuse/Create snapshot
        if snapshot_id:
            snapshot = esh_driver._connection.get_snapshot(snapshot_id)
            if not snapshot:
                return failure_response(
                    status.HTTP_400_BAD_REQUEST,
                    "Snapshot %s not found. Process aborted."
                    % snapshot_id)
        else:
            # Normal flow, create a snapshot from the volume
            if not esh_volume:
                return volume_not_found(volume_id)
            if esh_volume.extra['status'].lower() != 'available':
                return failure_response(
                    status.HTTP_400_BAD_REQUEST,
                    "Volume status must be 'available'. "
                    "Did you detach the volume?")

            snapshot = esh_driver._connection.ex_create_snapshot(
                esh_volume, display_name, description)
            if not snapshot:
                return failure_response(
                    status.HTTP_400_BAD_REQUEST,
                    "Snapshot not created. Process aborted.")
        # STEP 2 - Create volume from snapshot
        try:
            success, esh_volume = create_esh_volume(esh_driver, identity_uuid,
                                                display_name, size,
                                                description, metadata,
                                                snapshot=snapshot)
            if not success:
                return failure_response(
                    status.HTTP_500_INTERNAL_SERVER_ERROR,
                    'Volume creation failed. Contact support')
            # Volume creation succeeded
            core_volume = convert_esh_volume(esh_volume, provider_uuid,
                                             identity_uuid, user)
            serialized_data = VolumeSerializer(
                core_volume,
                context={'request': request}).data
            return Response(serialized_data, status=status.HTTP_201_CREATED)
        except OverQuotaError as oqe:
            return over_quota(oqe)
        except ConnectionFailure:
            return connection_failure(provider_uuid, identity_uuid)
        except LibcloudInvalidCredsError:
            return invalid_creds(provider_uuid, identity_uuid)


class VolumeSnapshotDetail(AuthAPIView):

    """
    Details of specific volume on Identity.
    """

    def get(self, request, provider_uuid, identity_uuid, snapshot_id):
        """
        """
        try:
            esh_driver = prepare_driver(request, provider_uuid, identity_uuid)
        except ProviderNotActive as pna:
            return inactive_provider(pna)
        except Exception as e:
            return failure_response(
                status.HTTP_409_CONFLICT,
                e.message)
        if not esh_driver:
            return invalid_creds(provider_uuid, identity_uuid)
        snapshot = esh_driver._connection.get_snapshot(snapshot_id)
        if not snapshot:
            return snapshot_not_found(snapshot_id)
        response = Response(snapshot)
        return response

    def delete(self, request, provider_uuid, identity_uuid, snapshot_id):
        """
        Destroys the volume and updates the DB
        """
        # Ensure volume exists
        try:
            esh_driver = prepare_driver(request, provider_uuid, identity_uuid)
        except ProviderNotActive as pna:
            return inactive_provider(pna)
        except Exception as e:
            return failure_response(
                status.HTTP_409_CONFLICT,
                e.message)
        if not esh_driver:
            return invalid_creds(provider_uuid, identity_uuid)
        snapshot = esh_driver._connection.get_snapshot(snapshot_id)
        if not snapshot:
            return snapshot_not_found(snapshot_id)
        delete_success = esh_driver._connection.ex_delete_snapshot(snapshot)
        # NOTE: Always false until icehouse...
        #    return failure_response(
        #        status.HTTP_400_BAD_REQUEST,
        #        % snapshot_id)
        return Response(status=status.HTTP_204_NO_CONTENT)


class VolumeList(AuthAPIView):

    """
    List all volumes on Identity.
    """

    def get(self, request, provider_uuid, identity_uuid):
        """
        Retrieves list of volumes and updates the DB
        """
        user = request.user
        try:
            esh_driver = prepare_driver(request, provider_uuid, identity_uuid)
        except ProviderNotActive as pna:
            return inactive_provider(pna)
        except Exception as e:
            return failure_response(
                status.HTTP_409_CONFLICT,
                e.message)
        if not esh_driver:
            return invalid_creds(provider_uuid, identity_uuid)
        volume_list_method = esh_driver.list_volumes

        if AccountProvider.objects.filter(identity__uuid=identity_uuid):
            # Instance list method changes when using the OPENSTACK provider
            volume_list_method = esh_driver.list_all_volumes
        try:
            esh_volume_list = volume_list_method()
        except (socket_error, ConnectionFailure):
            return connection_failure(provider_uuid, identity_uuid)
        except LibcloudBadResponseError:
            return malformed_response(provider_uuid, identity_uuid)
        except LibcloudInvalidCredsError:
            return invalid_creds(provider_uuid, identity_uuid)
        except Exception:
            logger.exception("Uncaught Exception in Volume list method")
            return failure_response(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                'Volume list method failed. Contact support')

        core_volume_list = [convert_esh_volume(volume, provider_uuid,
                                               identity_uuid, user)
                            for volume in esh_volume_list]
        serializer = VolumeSerializer(core_volume_list,
                                      context={'request': request}, many=True)
        response = Response(serializer.data)
        return response

    def post(self, request, provider_uuid, identity_uuid):
        """
        Creates a new volume and adds it to the DB
        """
        user = request.user
        try:
            membership = IdentityMembership.objects.get(
                identity__uuid=identity_uuid,
                member__name=user.username)
        except:
            return failure_response(
                status.HTTP_409_CONFLICT,
                "Identity %s is invalid -OR- User %s does not have the appropriate IdentityMembership." % (identity_uuid, user))
        try:
            driver = prepare_driver(request, provider_uuid, identity_uuid)
        except ProviderNotActive as pna:
            return inactive_provider(pna)
        except Exception as e:
            return failure_response(
                status.HTTP_409_CONFLICT,
                e.message)
        if not driver:
            return invalid_creds(provider_uuid, identity_uuid)
        data = request.data
        missing_keys = valid_volume_post_data(data)
        if missing_keys:
            return keys_not_found(missing_keys)
        # Pass arguments
        name = data.get('name')
        size = data.get('size')
        # Optional fields
        description = data.get('description')
        image_id = data.get('image')
        if image_id:
            image = driver.get_machine(image_id)
            image_size = image._connection.get_size(image._image)
            if int(size) > image_size + 4:
                return failure_response(
                    status.HTTP_400_BAD_REQUEST,
                    "Volumes created from images cannot exceed "
                    "more than 4GB greater than the size of "
                    "the image: %s GB" % image_size)
        else:
            image = None
        snapshot_id = data.get('snapshot')
        if snapshot_id:
            snapshot = driver._connection.ex_get_snapshot(image_id)
        else:
            snapshot = None
        try:
            success, esh_volume = create_esh_volume(driver, user.username, identity_uuid,
                                                name, size, description,
                                                snapshot=snapshot, image=image)
        except BaseHTTPError as http_error:
            if 'Requested volume or snapshot exceed' in http_error.message:
                return over_quota(http_error)
            return failure_response(status.HTTP_400_BAD_REQUEST, http_error.message)
        except OverQuotaError as oqe:
            return over_quota(oqe)
        except ConnectionFailure:
            return connection_failure(provider_uuid, identity_uuid)
        except LibcloudBadResponseError:
            return malformed_response(provider_uuid, identity_uuid)
        except LibcloudInvalidCredsError:
            return invalid_creds(provider_uuid, identity_uuid)
        if not success:
            return failure_response(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                'Volume creation failed. Contact support')
        # Volume creation succeeded
        core_volume = convert_esh_volume(esh_volume, provider_uuid,
                                         identity_uuid, user)
        serialized_data = VolumeSerializer(core_volume,
                                           context={'request': request}).data
        return Response(serialized_data, status=status.HTTP_201_CREATED)


class Volume(AuthAPIView):

    """
    Details of specific volume on Identity.
    """

    def get(self, request, provider_uuid, identity_uuid, volume_id):
        """
        """
        user = request.user
        try:
            esh_driver = prepare_driver(request, provider_uuid, identity_uuid)
        except ProviderNotActive as pna:
            return inactive_provider(pna)
        except Exception as e:
            return failure_response(
                status.HTTP_409_CONFLICT,
                e.message)

        if not esh_driver:
            return invalid_creds(provider_uuid, identity_uuid)
        try:
            esh_volume = esh_driver.get_volume(volume_id)
        except ConnectionFailure:
            return connection_failure(provider_uuid, identity_uuid)
        except LibcloudInvalidCredsError:
            return invalid_creds(provider_uuid, identity_uuid)
        except Exception as exc:
            logger.exception("Encountered a generic exception. "
                             "Returning 409-CONFLICT")
            return failure_response(status.HTTP_409_CONFLICT,
                                    str(exc.message))
        if not esh_volume:
            try:
                source = InstanceSource.objects.get(
                    identifier=volume_id,
                    provider__uuid=provider_uuid)
                source.end_date = datetime.now()
                source.save()
            except (InstanceSource.DoesNotExist, CoreVolume.DoesNotExist):
                pass
            return volume_not_found(volume_id)
        core_volume = convert_esh_volume(esh_volume, provider_uuid,
                                         identity_uuid, user)
        serialized_data = VolumeSerializer(core_volume,
                                           context={'request': request}).data
        response = Response(serialized_data)
        return response

    def patch(self, request, provider_uuid, identity_uuid, volume_id):
        """
        Updates DB values for volume
        """
        user = request.user
        data = request.data
        # Ensure volume exists
        try:
            esh_driver = prepare_driver(request, provider_uuid, identity_uuid)
        except ProviderNotActive as pna:
            return inactive_provider(pna)
        except Exception as e:
            return failure_response(
                status.HTTP_409_CONFLICT,
                e.message)

        if not esh_driver:
            return invalid_creds(provider_uuid, identity_uuid)
        try:
            esh_volume = esh_driver.get_volume(volume_id)
        except ConnectionFailure:
            return connection_failure(provider_uuid, identity_uuid)
        except LibcloudInvalidCredsError:
            return invalid_creds(provider_uuid, identity_uuid)
        except Exception as exc:
            logger.exception("Encountered a generic exception. "
                             "Returning 409-CONFLICT")
            return failure_response(status.HTTP_409_CONFLICT,
                                    str(exc.message))
        if not esh_volume:
            return volume_not_found(volume_id)
        core_volume = convert_esh_volume(esh_volume, provider_uuid,
                                         identity_uuid, user)
        serializer = VolumeSerializer(core_volume, data=data,
                                      context={'request': request},
                                      partial=True)
        if serializer.is_valid():
            serializer.save()
            _update_volume_metadata(
                esh_driver, esh_volume, data)
            response = Response(serializer.data)
            return response
        else:
            return failure_response(
                status.HTTP_400_BAD_REQUEST,
                serializer.errors)

    def put(self, request, provider_uuid, identity_uuid, volume_id):
        """
        Updates DB values for volume
        """
        user = request.user
        data = request.data

        # Ensure volume exists
        try:
            esh_driver = prepare_driver(request, provider_uuid, identity_uuid)
        except ProviderNotActive as pna:
            return inactive_provider(pna)
        except Exception as e:
            return failure_response(
                status.HTTP_409_CONFLICT,
                e.message)

        if not esh_driver:
            return invalid_creds(provider_uuid, identity_uuid)
        try:
            esh_volume = esh_driver.get_volume(volume_id)
        except ConnectionFailure:
            return connection_failure(provider_uuid, identity_uuid)
        except LibcloudInvalidCredsError:
            return invalid_creds(provider_uuid, identity_uuid)
        except Exception as exc:
            logger.exception("Encountered a generic exception. "
                             "Returning 409-CONFLICT")
            return failure_response(status.HTTP_409_CONFLICT,
                                    str(exc.message))
        if not esh_volume:
            return volume_not_found(volume_id)
        core_volume = convert_esh_volume(esh_volume, provider_uuid,
                                         identity_uuid, user)
        serializer = VolumeSerializer(core_volume, data=data,
                                      context={'request': request})
        if serializer.is_valid():
            serializer.save()
            _update_volume_metadata(
                esh_driver, esh_volume, data)
            response = Response(serializer.data)
            return response
        else:
            failure_response(
                status.HTTP_400_BAD_REQUEST,
                serializer.errors)

    def delete(self, request, provider_uuid, identity_uuid, volume_id):
        """
        Destroys the volume and updates the DB
        """
        user = request.user
        # Ensure volume exists
        try:
            esh_driver = prepare_driver(request, provider_uuid, identity_uuid)
        except ProviderNotActive as pna:
            return inactive_provider(pna)
        except Exception as e:
            return failure_response(
                status.HTTP_409_CONFLICT,
                e.message)

        if not esh_driver:
            return invalid_creds(provider_uuid, identity_uuid)
        try:
            esh_volume = esh_driver.get_volume(volume_id)
        except ConnectionFailure:
            return connection_failure(provider_uuid, identity_uuid)
        except LibcloudInvalidCredsError:
            return invalid_creds(provider_uuid, identity_uuid)
        except Exception as exc:
            logger.exception("Encountered a generic exception. "
                             "Returning 409-CONFLICT")
            return failure_response(status.HTTP_409_CONFLICT,
                                    str(exc.message))
        if not esh_volume:
            return volume_not_found(volume_id)
        core_volume = convert_esh_volume(esh_volume, provider_uuid,
                                         identity_uuid, user)
        # Delete the object, update the DB
        esh_driver.destroy_volume(esh_volume)
        core_volume.end_date = now()
        core_volume.save()
        # Return the object
        serialized_data = VolumeSerializer(core_volume,
                                           context={'request': request}).data
        response = Response(serialized_data)
        return response


class BootVolume(AuthAPIView):

    """
    Launch an instance using this volume as the source
    """

    def _select_source_key(self, data):
        if 'image_id' in data:
            return "image_id"
        elif 'snapshot_id' in data:
            return "snapshot_id"
        elif 'volume_id' in data:
            return "volume_id"
        else:
            return None

    def post(self, request, provider_uuid, identity_uuid, volume_id=None):
        user = request.user
        data = request.data

        missing_keys = valid_launch_data(data)
        if missing_keys:
            return keys_not_found(missing_keys)
        source = None
        name = data.pop('name')
        size_id = data.pop('size')
        key_name = self._select_source_key(data)
        if not key_name:
            return failure_response(
                status.HTTP_400_BAD_REQUEST,
                'Source could not be acquired. Did you send: ['
                'snapshot_id/volume_id/image_id] ?')
        try:
            core_instance = create_bootable_volume(
                request.user, provider_uuid, identity_uuid,
                name, size_id, volume_id, source_hint=key_name,
                **data)
        except Exception as exc:
            message = exc.message
            return failure_response(
                status.HTTP_409_CONFLICT,
                message)

        serialized_data = InstanceSerializer(core_instance,
                                             context={'request': request}).data
        response = Response(serialized_data)
        return response


def valid_launch_data(data):
    """
    Return any missing required post key names.
    """
    required = ['name', 'size']
    return [key for key in required
            # Key must exist and have a non-empty value.
            if key not in data or
            (isinstance(data[key], str) and len(data[key]) > 0)]


def valid_snapshot_post_data(data):
    """
    Return any missing required post key names.
    """
    required = ['display_name', 'volume_id', 'size']
    return [key for key in required
            # Key must exist and have a non-empty value.
            if key not in data or
            (isinstance(data[key], str) and len(data[key]) > 0)]


def valid_snapshot_post_data(data):
    """
    Return any missing required post key names.
    """
    required = ['display_name', 'volume_id', 'size']
    return [key for key in required
            # Key must exist and have a non-empty value.
            if key not in data or
            (isinstance(data[key], str) and len(data[key]) > 0)]


def valid_volume_post_data(data):
    """
    Return any missing required post key names.
    """
    required = ['name', 'size']
    return [key for key in required
            # Key must exist and have a non-empty value.
            if key not in data or
            (isinstance(data[key], str) and len(data[key]) > 0)]


def keys_not_found(missing_keys):
    return failure_response(
        status.HTTP_400_BAD_REQUEST,
        'Missing required POST datavariables : %s' % missing_keys)


def snapshot_not_found(snapshot_id):
    return failure_response(
        status.HTTP_404_NOT_FOUND,
        'Snapshot %s does not exist' % snapshot_id)


def volume_not_found(volume_id):
    return failure_response(
        status.HTTP_404_NOT_FOUND,
        'Volume %s does not exist' % volume_id)


def over_quota(quota_exception):
    return failure_response(
        status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        quota_exception.message)
