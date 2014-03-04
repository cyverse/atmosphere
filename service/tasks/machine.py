import time

from threepio import logger

from celery.decorators import task
from celery.result import allow_join_result

from chromogenic.tasks import machine_imaging_task, migrate_instance_task
from chromogenic.drivers.openstack import ImageManager as OSImageManager
from chromogenic.drivers.eucalyptus import ImageManager as EucaImageManager

from atmosphere import settings
from atmosphere.celery import app

from core.email import send_image_request_email
from core.models.machine_request import MachineRequest, process_machine_request
from core.models.identity import Identity

from service.driver import get_admin_driver
from service.deploy import freeze_instance, sync_instance
from service.tasks.driver import deploy_to

# For development
try:
    import ipdb
except ImportError:
    ipdb = False
    pass


def start_machine_imaging(machine_request, delay=False):
    """
    Builds up a machine imaging task using core.models.machine_request
    delay - If true, wait until task is completed before returning
    """
    machine_request.status = 'imaging'
    machine_request.save()
    instance_id = machine_request.instance.provider_alias

    (orig_managerCls, orig_creds,
     dest_managerCls, dest_creds) = machine_request.prepare_manager()
    imaging_args = machine_request.get_imaging_args()

    #Step 1 - On OpenStack, sync/freeze BEFORE starting migration/imaging
    init_task = None
    #if orig_managerCls == OSImageManager:  # TODO:AND if instance still running
    #    freeze_task = freeze_instance_task.si(
    #        machine_request.instance.created_by_identity_id, instance_id)
    #    init_task = freeze_task
    if dest_managerCls and dest_creds != orig_creds:
        #Will run machine imaging task..
        migrate_task = migrate_instance_task.si(
            orig_managerCls, orig_creds, dest_managerCls, dest_creds,
            **imaging_args)
        if not init_task:
            init_task = migrate_task
        else:
            init_task.link(migrate_task)
    else:
        image_task = machine_imaging_task.si(
            orig_managerCls, orig_creds, imaging_args)
        if not init_task:
            init_task = image_task
        else:
            init_task.link(image_task)
    #The new image ID will be the first argument in process_request
    process_task = process_request.s(machine_request.id)
    if dest_managerCls and dest_creds != orig_creds:
        migrate_task.link(process_task)
    else:
        image_task.link(process_task)

    async = init_task.apply_async(
        link_error=machine_request_error.s(machine_request.id),
        )
    if delay:
        async.get()
    return async


def set_machine_request_metadata(machine_request, image_id):
    (orig_managerCls, orig_creds,
        new_managerCls, new_creds) = machine_request.prepare_manager()
    if new_managerCls:
        manager = new_managerCls(**new_creds)
    else:
        manager = orig_managerCls(**orig_creds)
    if not hasattr(manager, 'admin_driver'):
        return
    #Update metadata on rtwo/libcloud machine -- NOT a glance machine
    machine = manager.admin_driver.get_machine(image_id)
    lc_driver = manager.admin_driver._connection
    if not hasattr(lc_driver, 'ex_set_image_metadata'):
        return
    metadata = lc_driver.ex_get_image_metadata(machine)

    if machine_request.new_machine_description:
        metadata['description'] = machine_request.new_machine_description
    if machine_request.new_machine_tags:
        metadata['tags'] = machine_request.new_machine_tags
    logger.info("LC Driver:%s - Machine:%s - Metadata:%s"
                % (lc_driver, machine.id, metadata))
    lc_driver.ex_set_image_metadata(machine, metadata)
    return machine


#NOTE: Is this different than the 'task' found in celery.decorators?
@task(name='machine_request_error')
def machine_request_error(task_uuid, machine_request_id):
    logger.info("machine_request_id=%s" % machine_request_id)
    logger.info("task_uuid=%s" % task_uuid)

    result = app.AsyncResult(task_uuid)
    with allow_join_result():
        exc = result.get(propagate=False)
    err_str = "ERROR - %r Exception:%r" % (result.result, result.traceback,)
    logger.error(err_str)
    machine_request = MachineRequest.objects.get(id=machine_request_id)
    machine_request.status = err_str
    machine_request.save()


@task(name='process_request', queue="imaging", ignore_result=False)
def process_request(new_image_id, machine_request_id):
    #if ipdb:
    #    ipdb.set_trace()
    machine_request = MachineRequest.objects.get(id=machine_request_id)
    machine_request.status = 'processing - %s' % new_image_id
    machine_request.save()
    invalidate_machine_cache(machine_request)
    set_machine_request_metadata(machine_request, new_image_id)
    process_machine_request(machine_request, new_image_id)
    send_image_request_email(machine_request.new_machine_owner,
                             machine_request.new_machine,
                             machine_request.new_machine_name)


def invalidate_machine_cache(machine_request):
    """
    The new image won't populate in the machine list unless
    the list is cleared.
    """
    from api import get_esh_driver
    provider = machine_request.instance.\
        provider_machine.provider
    driver = get_admin_driver(provider)
    if not driver:
        return
    driver.provider.machineCls.invalidate_provider_cache(driver.provider)


@task(name='freeze_instance_task', ignore_result=False, queue="imaging")
def freeze_instance_task(identity_id, instance_id, **celery_task_args):
    from api import get_esh_driver
    identity = Identity.objects.get(id=identity_id)
    driver = get_esh_driver(identity)
    kwargs = {}
    private_key = "/opt/dev/atmosphere/extras/ssh/id_rsa"
    kwargs.update({'ssh_key': private_key})
    kwargs.update({'timeout': 120})

    si_script = sync_instance()
    kwargs.update({'deploy': si_script})

    instance = driver.get_instance(instance_id)
    driver.deploy_to(instance, **kwargs)

    fi_script = freeze_instance()
    kwargs.update({'deploy': fi_script})
    driver.deploy_to(instance, **kwargs)
