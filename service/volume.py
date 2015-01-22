from djcelery.app import app
from django.conf import settings

from threepio import logger

from core.models.quota import get_quota, has_storage_count_quota,\
        has_storage_quota
from core.models.identity import Identity

from service.instance import network_init
from service.exceptions import OverQuotaError
from service import task
def update_volume_metadata(esh_driver, esh_volume,
        metadata={}):
    """
    NOTE: This will NOT WORK for TAGS until openstack
    allows JSONArrays as values for metadata!
    NOTE: This will NOT replace missing metadata tags..
    ex:
    Start: ('a':'value','c':'value')
    passed: c=5
    End: ('a':'value', 'c':5)
    """
    wait_time = 1
    if not esh_volume:
        return {}
    volume_id = esh_volume.id

    if not hasattr(esh_driver._connection, 'ex_update_volume_metadata'):
        logger.warn("EshDriver %s does not have function 'ex_update_volume_metadata'"
                    % esh_driver._connection.__class__)
        return {}
    data = esh_volume.extra.get('metadata',{})
    data.update(metadata)
    try:
        return esh_driver._connection.ex_update_volume_metadata(esh_volume, data)
    except Exception, e:
        logger.exception("Error updating the metadata")
        if 'incapable of performing the request' in e.message:
            return {}
        else:
            raise

def create_volume(esh_driver, identity_uuid, name, size,
                  description=None, metadata=None, snapshot=None, image=None):
    identity = Identity.objects.get(uuid=identity_uuid)
    quota = get_quota(identity_uuid)
    if not has_storage_quota(esh_driver, quota, size):
        raise OverQuotaError(
                message="Maximum total size of Storage Volumes Exceeded")
    if not has_storage_count_quota(esh_driver, quota, 1):
        raise OverQuotaError(
                message="Maximum # of Storage Volumes Exceeded")
    #NOTE: Calling non-standard create_volume_obj so we know the ID
    # of newly created volume. Libcloud just returns 'True'... --Steve
    success, esh_volume = esh_driver.create_volume(
        size=size,
        name=name,
        metadata=metadata,
        snapshot=snapshot,
        image=image)
    return success, esh_volume



def boot_volume(driver, core_identity_uuid,
                name=None, size_alias=None,
                #One of these values is required:
                volume_alias=None, snapshot_alias=None, machine_alias=None,
                #Depending on those values, these kwargs may/may not be used.
                boot_index=0, shutdown=False, volume_size=None):
    """
    return CoreInstance
    """
    core_identity = CoreIdentity.objects.get(uuid=core_identity_uuid)

    esh_instance, token, instance_password = launch_bootable_volume(
            driver, core_identity.uuid, size_alias=size_alias,
            name=name,
            volume_alias=volume_alias, snapshot_alias=snapshot_alias,
            machine_alias=machine_alias, boot_index=boot_index,
            shutdown=shutdown, volume_size=volume_size)
    #Convert esh --> core
    core_instance = convert_esh_instance(
        driver, esh_instance, core_identity.provider.uuid, core_identity.uuid,
        core_identity.created_by, token, instance_password)

    esh_size = esh_driver.get_size(esh_instance.size.id)
    core_size = convert_esh_size(esh_size, core_identity.provider.uuid)

    core_instance.update_history(
        core_instance.esh.extra['status'],
        core_size,
        #3rd arg is task OR tmp_status
        core_instance.esh.extra.get('task') or
        core_instance.esh.extra.get('metadata', {}).get('tmp_status'),
        first_update=True)


def launch_bootable_volume(driver, core_identity_uuid, size_alias,
                name=None,
                #One of these values is required:
                volume_alias=None, snapshot_alias=None, machine_alias=None,
                #Depending on those values, these kwargs may/may not be used.
                boot_index=0, shutdown=False, volume_size=None):
    """
    return 3-tuple: (esh_instance, instance_token, instance_password)
    """

    core_identity = CoreIdentity.objects.get(uuid=core_identity_uuid)

    size = driver.get_size(size_alias)
    machine = None
    snapshot = None
    volume = None
    if machine_alias:
        #Gather the machine object
        machine = driver.get_machine(machine_alias)
        if not machine:
            raise ValueError(
                "Machine %s could not be located with this driver"
                % machine_alias)
    elif snapshot_alias:
        #Gather the snapshot object
        snapshot = driver.get_snapshot(snapshot_alias)
        if not snapshot:
            raise ValueError(
                "Snapshot %s could not be located with this driver"
                % snapshot_alias)
    elif volume_alias:
        #Gather the volume object
        volume = driver.get_volume(volume_alias)
        if not volume:
            raise ValueError(
                "Volume %s could not be located with this driver"
                % volume_alias)
    else:
        raise ValueError("To boot a volume, you must select a source alias:"
                " [machine_alias, volume_alias, snapshot_alias]")

    try:
        username = driver.identity.user.username
    except Exception, no_username:
        username = core_identity.created_by.username

    instance_token = str(uuid.uuid4())
    #create a unique one-time password for instance root user
    instance_password = str(uuid.uuid4())

    if isinstance(driver.provider, OSProvider):
        security_group_init(core_identity)
        network = network_init(core_identity)
        keypair_init(core_identity)
        credentials = core_identity.get_credentials()
        tenant_name = credentials.get('ex_tenant_name')
        ex_metadata = {'tmp_status': 'initializing',
                       'tenant_name': tenant_name,
                       'creator': '%s' % username}
        ex_keyname = settings.ATMOSPHERE_KEYPAIR_NAME
        boot_success, new_instance = driver.boot_volume(
                name=name, image=machine, snapshot=snapshot, volume=volume,
                boot_index=boot_index, shutdown=shutdown,
                #destination_type=destination_type,
                volume_size=volume_size, size=size, ex_metadata=ex_metadata,
                ex_keyname=ex_keyname, networks=[network],
                ex_admin_pass=instance_password)
        #Used for testing.. Eager ignores countdown
        if app.conf.CELERY_ALWAYS_EAGER:
            logger.debug("Eager Task, wait 1 minute")
            time.sleep(1*60)
        # call async task to deploy to instance.
        task.deploy_init_task(driver, new_instance, username,
                              instance_password, instance_token)
    else:
        raise ValueError("The Provider: %s can't create bootable volumes"
                         % driver.provider)
    return (new_instance, instance_token, instance_password)
