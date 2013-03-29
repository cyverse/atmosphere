import re

from datetime import datetime

from celery.decorators import task

from atmosphere.logger import logger

from core.email import send_image_request_email
from core.models.machine import createProviderMachine
from core.models.tag import Tag

from service.drivers.eucalyptusImageManager import\
    ImageManager as EucaImageManager
from service.drivers.openstackImageManager import\
    ImageManager as OSImageManager
from service.drivers.migrate import EucaToOpenstack as EucaOSMigrater


def select_and_build_image(machine_request):
    old_provider = machine_request.instance.provider_machine\
        .provider.type.name.lower()
    new_provider = machine_request.new_machine_provider.type.name.lower()
    new_image_id = None

    if old_provider == 'eucalyptus':
        if new_provider == 'eucalyptus':
            logger.info('Create euca image from euca image')
            manager = EucaImageManager()
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
            )
        elif new_provider == 'openstack':
            logger.info('Create openstack image from euca image')
            manager = EucaOSMigrater()
            new_image_id = manager.migrate_instance(
                machine_request.instance.provider_alias,
                machine_request.new_machine_name)
    elif old_provider == 'openstack':
        if new_provider == 'eucalyptus':
            logger.info('Create euca image from openstack image')
            #TODO: Replace with OSEucaMigrater when this feature is complete
            new_image_id = None
        elif new_provider == 'openstack':
            logger.info('Create openstack image from openstack image')
            manager = OSImageManager()
            new_image_id = manager.create_image(
                machine_request.instance.provider_alias,
                machine_request.new_machine_name
            )

    return new_image_id


@task()
def machineExportTask(machine_export):
    pass


@task()
def machineImagingTask(machine_request):
    try:
        machine_request.status = 'processing'
        machine_request.save()
        logger.debug('%s' % machine_request)
        new_image_id = select_and_build_image(machine_request)
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
    except Exception, e:
        logger.error(e)
        machine_request.status = 'error'
        machine_request.save()
        return None
