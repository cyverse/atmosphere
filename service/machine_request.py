from chromogenic.tasks import machine_imaging_task
from chromogenic.drivers.openstack import ImageManager as OSImageManager
from chromogenic.drivers.eucalyptus import ImageManager as EucaImageManager

from atmosphere import settings

def start_machine_imaging(machine_request, delay=False):
    """
    Builds a machine imaging task using the machine_request
    delay - If true, wait until task is completed before returning
    """
    #TODO: Logic for if delay = True..
    from service.tasks.machine import process_request
    machine_request.status = 'processing'
    machine_request.save()
    manager, args, kwargs = prepare_request(machine_request)
    machine_imaging_task.si(manager, args, kwargs).apply_async(
            link=process_request.subtask((machine_request.id,)))
#TODO:
# After request is finished:
#

def prepare_request(machine_request):
    manager = machine_request.generate_manager()
    local_download_dir = settings.LOCAL_STORAGE
    if isinstance(manager, EucaImageManager):
        meta_name = machine_request._get_meta_name()
        public_image = machine_request.is_public()
        #Splits the string by ", " OR " " OR "\n" to create the list
        private_users = machine_request.get_access_list()
        exclude = machine_request.get_exclude_files()
        #Create image on image manager
        args = machine_request.instance.provider_alias
        kwargs = {
            "image_name" : machine_request.new_machine_name,
            "public" : public_image,
            "private_user_list" : private_users,
            "exclude" : exclude,
            "meta_name" : meta_name,
            "local_download_dir" : local_download_dir
        }
    elif isinstance(manager, OSImageManager):
        args = (machine_request.instance.provider_alias,
                machine_request.new_machine_name)
        kwargs = {
            "local_download_dir": local_download_dir
        }
    elif isinstance(manager, EucaOSMigrater):
        args = (machine_request.instance.provider_alias,
            machine_request.new_machine_name)
        kwargs = {"local_download_dir" : local_download_dir}
    return (manager, args, kwargs)


def set_machine_request_metadata(machine_request, machine):
    manager = machine_request.generate_manager()
    lc_driver = manager.driver
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


