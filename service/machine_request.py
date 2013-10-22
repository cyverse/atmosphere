from chromogenic.tasks import machine_imaging_task, machine_migration_task
from chromogenic.drivers.openstack import ImageManager as OSImageManager
from chromogenic.drivers.eucalyptus import ImageManager as EucaImageManager

from atmosphere import settings

def start_machine_imaging(machine_request, delay=False):
    """
    Builds a machine imaging task using the machine_request
    delay - If true, wait until task is completed before returning
    """
    #TODO: Logic for if delay = True..
    from service.tasks.machine import process_request, freeze_instance_task
    machine_request.status = 'processing'
    machine_request.save()
    instance_id = machine_request.instance.provider_alias

    (orig_managerCls, orig_creds,
     dest_managerCls, dest_creds) = machine_request.prepare_manager()
    imaging_args = machine_request.get_imaging_args()

    #Step 1 - On OpenStack, sync/freeze BEFORE starting migration/imaging
    if orig_managerCls == OSImageManager:
        freeze_task = freeze_instance_task.si(machine_request.id, instance_id)
        init_task = freeze_task
    if dest_managerCls and dest_creds != orig_creds:
        #Will run machine imaging task..
        migrate_task = machine_migration_task.si(
                orig_managerCls, orig_creds, dest_managerCls, dest_creds,
                **imaging_args)
        if not init_task:
            init_task = migrate_task
        else:
            init_task.link(migrate_task)
    else:
        image_task = machine_imaging_task.si(orig_managerCls, orig_creds,
                                             **imaging_args)
        if not init_task:
            init_task = image_task
        else:
            init_task.link(image_task)
    process_task = process_request.subtask((machine_request.id,))
    #After the init_task is completed (And any other links..)
    init_task.link(process_task)
    init_task.apply_async()


#TODO:
# After request is finished:
#

def set_machine_request_metadata(machine_request, machine):
    (orig_managerCls, orig_creds,
        new_managerCls, new_creds) = machine_request.prepare_manager()
    if not new_manager:
        manager = orig_managerCls(**orig_creds)
    else:
        manager = new_managerCls(**new_creds)
    lc_driver = manager.admin_driver._connection
    if not hasattr(lc_driver, 'ex_set_image_metadata'):
        return
    lc_driver.ex_set_image_metadata(machine, {'deployed':'True'})
    if machine_request.new_machine_description:
        metadata['description'] = machine_request.new_machine_description
    if machine_request.new_machine_tags:
        metadata['tags'] = machine_request.new_machine_tags
    logger.info("LC Driver:%s - Machine:%s - Metadata:%s" % (lc_driver,
            machine.id, metadata))
    lc_driver.ex_set_image_metadata(machine, metadata)
    return machine


