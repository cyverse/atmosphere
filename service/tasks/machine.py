import re

from datetime import datetime

from celery.decorators import task

from threepio import logger

from core.email import send_image_request_email
from core.models.machine import createProviderMachine
from core.models.tag import Tag

from service.drivers.eucalyptusImageManager import\
    ImageManager as EucaImageManager
from service.drivers.openstackImageManager import\
    ImageManager as OSImageManager
from service.drivers.migrate import EucaOSMigrater

from atmosphere import settings

@task()
def machine_export_task(machine_export):
    pass

@task(name='machine_migration_task', ignore_result=True)
def machine_migration_task(new_machine_name, old_machine_id,
                           local_download_dir='/tmp',
                           migrate_from='eucalyptus',
                           migrate_to='openstack'):
        logger.debug("machine_migration_task task started at %s." % datetime.now())
        if migrate_from == 'eucalyptus' and migrate_to == 'openstack':
            manager = EucaOSMigrater(settings.EUCA_IMAGING_ARGS,
                                     settings.OPENSTACK_ARGS)
            manager.migrate_image(old_machine_id, new_machine_name,
                                  local_download_dir)
        else:
            raise Exception("Cannot migrate from %s to %s" % (migrate_from,
                                                              migrate_to))
        logger.debug("machine_migration_task task finished at %s." % datetime.now())

@task(name='machine_imaging_task', ignore_result=True)
def machine_imaging_task(machine_request, euca_imaging_creds, openstack_creds):
    try:
        machine_request.status = 'processing'
        machine_request.save()
        logger.debug('%s' % machine_request)
        local_download_dir = settings.LOCAL_STORAGE
        new_image_id = select_and_build_image(machine_request,
                euca_imaging_creds, openstack_creds, local_download_dir)
        if new_image_id is None:
            raise Exception('The image cannot be built as requested. '
                            + 'The provider combination is probably bad.')
        logger.info('New image created - %s' % new_image_id)

        #Build the new provider-machine object and associate
        new_machine = createProviderMachine(
            machine_request.new_machine_name, new_image_id,
            machine_request.new_machine_provider_id)
        generic_mach = new_machine.machine
        tags = [Tag.objects.get(name=tag) for tag in
                machine_request.new_machine_tags.split(',')] \
            if machine_request.new_machine_tags else []
        generic_mach.tags = tags
        generic_mach.description = machine_request.new_machine_description
        generic_mach.save()
        machine_request.new_machine = new_machine
        machine_request.end_date = datetime.now()
        machine_request.status = 'completed'
        machine_request.save()
        send_image_request_email(machine_request.new_machine_owner,
                                 machine_request.new_machine,
                                 machine_request.new_machine_name)
        return new_image_id
    except Exception as e:
        logger.exception(e)
        machine_request.status = 'error - %s' % (e,)
        machine_request.save()
        return None

def select_and_build_image(machine_request, euca_imaging_creds,
                           openstack_creds, local_download_dir='/tmp'):
    """
    Directing traffic between providers
    Fill out all available fields using machine request data
    """
    old_provider = machine_request.instance.provider_machine\
        .provider.type.name.lower()
    new_provider = machine_request.new_machine_provider.type.name.lower()
    new_image_id = None
    
    if old_provider == 'eucalyptus':
        if new_provider == 'eucalyptus':
            logger.info('Create euca image from euca image')
            manager = EucaImageManager(**euca_imaging_creds)
            #Build the meta_name so we can re-start if necessary
            meta_name = '%s_%s_%s_%s' % ('admin',
                machine_request.new_machine_owner.username,
                machine_request.new_machine_name.replace(
                    ' ','_').replace('/','-'),
                machine_request.start_date.strftime('%m%d%Y_%H%M%S'))
            new_image_id = manager.create_image(
                machine_request.instance.provider_alias,
                image_name=machine_request.new_machine_name,
                public=True if
                "public" in machine_request.new_machine_visibility.lower()
                else False,
                #Split the string by ", " OR " " OR "\n" to create the list
                private_user_list=re.split(', | |\n',
                                           machine_request.access_list),
                exclude=re.split(", | |\n",
                                 machine_request.exclude_files),
                meta_name=meta_name,
                local_download_dir=local_download_dir,
            )
        elif new_provider == 'openstack':
            logger.info('Create openstack image from euca image')
            manager = EucaOSMigrater(
                    euca_imaging_creds,
                    openstack_creds)
            new_image_id = manager.migrate_instance(
                machine_request.instance.provider_alias,
                machine_request.new_machine_name,
                local_download_dir=local_download_dir) 
    elif old_provider == 'openstack':
        if new_provider == 'eucalyptus':
            logger.info('Create euca image from openstack image')
            #TODO: Replace with OSEucaMigrater when this feature is complete
            new_image_id = None
        elif new_provider == 'openstack':
            logger.info('Create openstack image from openstack image')
            manager = OSImageManager(**openstack_creds)
            #NOTE: This will create a snapshot, (Private-?), but is not a full
            #fledged image
            new_image_id = manager.create_image(
                machine_request.instance.provider_alias,
                machine_request.new_machine_name,
                machine_request.new_machine_owner.username)
            #TODO: Grab the machine, then add image metadata here
            machine = [img for img in manager.list_images()
                       if img.id == new_image_id]
            if not machine:
                return
	    set_machine_request_metadata(manager, machine_request, machine)
    return new_image_id

def set_machine_request_metadata(manager, machine_request, machine):
    manager.driver.ex_set_image_metadata(machine, {'deployed':'True'})
    if machine_request.new_machine_description:
    	manager.driver.ex_set_image_metadata(machine, {'description':machine_request.new_machine_description})
    if machine_request.new_machine_tags:
    	manager.driver.ex_set_image_metadata(machine, {'tags':machine_request.new_machine_tags})
    return machine


