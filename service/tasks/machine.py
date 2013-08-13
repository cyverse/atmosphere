import re

from datetime import datetime

from celery.decorators import task

from threepio import logger

from core.email import send_image_request_email
from core.models.machine import createProviderMachine
from core.models.machine_request import process_machine_request

from service.accounts.openstack import AccountDriver as OSAccountDriver

from service.drivers.eucalyptusImageManager import\
    ImageManager as EucaImageManager
from service.drivers.openstackImageManager import\
    ImageManager as OSImageManager
from service.drivers.migrate import EucaOSMigrater

from service.drivers.virtualboxExportManager import\
    ExportManager

from atmosphere import settings

@task()
def machine_export_task(machine_export):
    logger.debug("machine_export_task task started at %s." % datetime.now())
    machine_export.status = 'processing'
    machine_export.save()

    local_download_dir = settings.LOCAL_STORAGE
    exp_provider = machine_export.instance.provider_machine\
        .provider.type.name.lower()

    manager = ExportManager(settings.EUCA_IMAGING_ARGS,
                            settings.OPENSTACK_ARGS)
    #ExportManager().eucalyptus/openstack()
    if 'euca' in exp_provider:
        export_fn = manager.eucalyptus
    elif 'openstack' in exp_provider:
        export_fn = manager.openstack
    else:
        raise Exception("Unknown Provider %s, expected eucalyptus/openstack"
                        % (exp_provider, ))

    meta_name = manager.euca_img_manager._format_meta_name(
        machine_export.export_name,
        machine_export.export_owner.username,
        timestamp_str = machine_export.start_date.strftime('%m%d%Y_%H%M%S'))

    md5_sum, url = export_fn(machine_export.instance.provider_alias,
                             machine_export.export_name,
                             machine_export.export_owner.username,
                             download_dir=local_download_dir,
                             meta_name=meta_name)
    #TODO: Pass in kwargs (Like md5sum, url, etc. that are useful)
    process_machine_export(machine_export, md5_sum=md5_sum, url=url)
    #TODO: Option to copy this file into iRODS
    #TODO: Option to upload this file into S3 
    #TODO: send an email with instructions on how/where to go from here

    logger.debug("machine_export_task task finished at %s." % datetime.now())
    pass

@task(name='machine_migration_task', ignore_result=True)
def machine_migration_task(new_machine_name, old_machine_id,
                           local_download_dir='/tmp',
                           migrate_from='eucalyptus',
                           migrate_to='openstack'):
    logger.debug("machine_migration_task task started at %s." % datetime.now())
    if migrate_from == 'eucalyptus' and migrate_to == 'openstack':
        manager = EucaOSMigrater(settings.EUCA_IMAGING_ARGS.copy(),
                                 settings.OPENSTACK_ARGS.copy())
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
        process_machine_request(machine_request, new_image_id)
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
    logger.info('Processing machine request to create a %s image from a %s'
                'instance' % (new_provider, old_provider))
    
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
            new_image_id = manager.create_image(
                machine_request.instance.provider_alias,
                machine_request.new_machine_name,
                local_download_dir=local_download_dir)
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
        metadata['description'] = machine_request.new_machine_description
    if machine_request.new_machine_tags:
        metadata['tags'] = machine_request.new_machine_tags
    logger.info("LC Driver:%s - Machine:%s - Metadata:%s" % (lc_driver,
            machine.id, metadata))
    lc_driver.ex_set_image_metadata(machine, metadata)
    return machine


