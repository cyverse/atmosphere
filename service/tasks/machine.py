import time

from threepio import logger

from celery.decorators import task
from celery.result import allow_join_result

from chromogenic.tasks import machine_imaging_task, migrate_instance_task

from atmosphere import settings
from atmosphere.celery import app

from core.email import \
        send_image_request_email, send_image_request_failed_email
from core.models.machine_request import MachineRequest, process_machine_request
from core.models.identity import Identity

from service.driver import get_admin_driver, get_esh_driver
from service.deploy import freeze_instance, sync_instance
from service.tasks.driver import deploy_to, wait_for_instance, destroy_instance


def _get_imaging_task(orig_managerCls, orig_creds,
                      dest_managerCls, dest_creds, imaging_args): 
    #NOTE: destManagerCls may == origManagerCls,
    #      but creds MUST be different for a migration.
    if dest_managerCls and dest_creds != orig_creds:
        migrate_task = migrate_instance_task.si(
            orig_managerCls, orig_creds, dest_managerCls, dest_creds,
            **imaging_args)
        return migrate_task
    else:
        image_task = machine_imaging_task.si(
            orig_managerCls, orig_creds, imaging_args)
        return image_task

def _recover_from_error(status_name):
    if not status_name:
        return False, status_name
    if 'exception' in status_name.lower():
        return True, status_name[status_name.find("(")+1:status_name.find(")")]
    return False, status_name

def start_machine_imaging(machine_request, delay=False):
    """
    Builds up a machine imaging task using core.models.machine_request
    delay - If true, wait until task is completed before returning
    """
    original_status = machine_request.status
    last_run_error, original_status = _recover_from_error(original_status)
    if last_run_error:
        machine_request.status = original_status
        machine_request.save()
    instance_id = machine_request.instance.provider_alias

    (orig_managerCls, orig_creds,
     dest_managerCls, dest_creds) = machine_request.prepare_manager()
    imaging_args = machine_request.get_imaging_args()
    admin_driver = machine_request.new_admin_driver()
    admin_ident = machine_request.new_admin_identity()

    imaging_error_task = machine_request_error.s(machine_request.id)

    #Task 2 = Imaging w/ Chromogenic
    imaging_task = _get_imaging_task(orig_managerCls, orig_creds,
                                     dest_managerCls, dest_creds,
                                     imaging_args)
    imaging_task.link_error(imaging_error_task)
    #Assume we are starting from the beginning.
    init_task = imaging_task
    #Task 2 = Process the machine request
    if 'processing' in original_status:
        #If processing, start here..
        image_id = machine_request.status.replace("processing - ","")
        logger.info("Start with processing:%s" % image_id)
        process_task = process_request.s(image_id, machine_request.id)
        init_task = process_task
    else:
        #Link from imaging to process..
        process_task = process_request.s(machine_request.id)
        imaging_task.link(process_task)
    process_task.link_error(imaging_error_task)

    #Task 3 = Validate the new image by launching an instance
    if 'validating' in original_status:
        image_id = machine_request.new_machine.identifier
        logger.info("Start with validating:%s" % image_id)
        #If validating, seed the image_id and start here..
        validate_task = validate_new_image.s(image_id, machine_request.id)
        init_task = validate_task
    else:
        validate_task = validate_new_image.s(machine_request.id)
        process_task.link(validate_task)

    #Task 4 = Wait for new instance to be 'active'
    wait_for_task = wait_for_instance.s(
            #NOTE: 1st arg, instance_id, passed from last task.
            admin_driver.__class__, 
            admin_driver.provider,
            admin_driver.identity,
            "active",
            return_id=True)
    validate_task.link(wait_for_task)
    validate_task.link_error(imaging_error_task)

    #Task 5 = Terminate the new instance on completion
    destroy_task = destroy_instance.s(
            admin_ident.id)
    wait_for_task.link(destroy_task)
    wait_for_task.link_error(imaging_error_task)
    #Task 6 - Finally, email the user that their image is ready!
    #NOTE: si == Ignore the result of the last task.
    email_task = imaging_complete.si(machine_request.id)
    destroy_task.link_error(imaging_error_task)
    destroy_task.link(email_task)

    email_task.link_error(imaging_error_task)
    #Set status to imaging ONLY if our initial task is the imaging task.
    if init_task == imaging_task:
        machine_request.status = 'imaging'
        machine_request.save()
    # Start the task.
    async = init_task.apply_async()
    if delay:
        async.get()
    return async


def set_machine_request_metadata(machine_request, image_id):
    admin_driver = machine_request.new_admin_driver()
    machine = admin_driver.get_machine(image_id)
    lc_driver = admin_driver._connection
    if not machine:
        logger.warn("Could not find machine with ID=%s" % image_id)
        return
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


@task(name='machine_request_error')
def machine_request_error(task_uuid, machine_request_id):
    logger.info("machine_request_id=%s" % machine_request_id)
    logger.info("task_uuid=%s" % task_uuid)
    machine_request = MachineRequest.objects.get(id=machine_request_id)

    result = app.AsyncResult(task_uuid)
    with allow_join_result():
        exc = result.get(propagate=False)
    err_str = "(%s) ERROR - %r Exception:%r" % (machine_request.status, result.result, result.traceback,)
    logger.error(err_str)
    send_image_request_failed_email(machine_request, err_str)
    machine_request = MachineRequest.objects.get(id=machine_request_id)
    machine_request.status = err_str
    machine_request.save()


@task(name='imaging_complete', queue="imaging", ignore_result=False)
def imaging_complete(machine_request_id):
    machine_request = MachineRequest.objects.get(id=machine_request_id)
    machine_request.status = 'completed'
    machine_request.save()
    send_image_request_email(machine_request.new_machine_owner,
                             machine_request.new_machine,
                             machine_request.new_machine_name)
    new_image_id = machine_request.new_machine.identifier
    return new_image_id

@task(name='process_request', queue="imaging", ignore_result=False)
def process_request(new_image_id, machine_request_id):
    """
    First, save the new image id so we can resume in case of failure.
    Then, Invalidate the machine cache to avoid a cache miss.
    Then, process the request by creating/updating all core objects related
    to this specific machine request.
    Finally, update the metadata on the provider.
    """
    machine_request = MachineRequest.objects.get(id=machine_request_id)
    machine_request.status = 'processing - %s' % new_image_id
    machine_request.save()
    #TODO: Best if we could 'broadcast' this to all running
    # Apache WSGI procs && celery 'imaging' procs
    invalidate_machine_cache(machine_request)
    process_machine_request(machine_request, new_image_id)
    return new_image_id


@task(name='validate_new_image', queue="imaging", ignore_result=False)
def validate_new_image(image_id, machine_request_id):
    machine_request = MachineRequest.objects.get(id=machine_request_id)
    machine_request.status = 'validating'
    machine_request.save()
    from service.instance import launch_esh_instance
    admin_driver = machine_request.new_admin_driver()
    admin_ident = machine_request.new_admin_identity()
    if not admin_driver:
        logger.warn("Need admin_driver functionality to auto-validate instance")
        return False
    if not admin_ident:
        logger.warn("Need to know the AccountProvider to auto-validate instance")
        return False
    # Attempt to launch using the admin_driver
    admin_driver.identity.user = admin_ident.created_by
    machine = admin_driver.get_machine(image_id)
    small_size = admin_driver.list_sizes()[0]
    (instance, token, password) = launch_esh_instance(
            admin_driver,
            machine.id,
            small_size.id,
            admin_ident,
            'Automated Image Verification - %s' % image_id,
            'atmoadmin',
            using_admin=True)
    return instance.id


def invalidate_machine_cache(machine_request):
    """
    The new image won't populate in the machine list unless
    the list is cleared.
    """
    provider = machine_request.instance.\
        provider_machine.provider
    driver = get_admin_driver(provider)
    if not driver:
        return
    driver.provider.machineCls.invalidate_provider_cache(driver.provider)


@task(name='freeze_instance_task', ignore_result=False, queue="imaging")
def freeze_instance_task(identity_id, instance_id, **celery_task_args):
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
