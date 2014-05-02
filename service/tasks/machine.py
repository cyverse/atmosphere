import time

from django.utils import timezone
from threepio import logger

from celery.decorators import task
from celery.result import allow_join_result

from chromogenic.tasks import machine_imaging_task, migrate_instance_task

from atmosphere import settings
from atmosphere.celery import app

from core.email import \
        send_image_request_email, send_image_request_failed_email
from core.models.machine_request import MachineRequest, process_machine_request
from core.models.machine_export import MachineExport, process_machine_export
from core.models.identity import Identity

from service.driver import get_admin_driver
from service.deploy import freeze_instance, sync_instance
from service.tasks.driver import deploy_to, wait_for, destroy_instance

# For development
try:
    import ipdb
except ImportError:
    ipdb = False
    pass


def start_machine_export(machine_export, delay=True):
    """
    Build up a machine export task using core.models.machine_export
    """
    machine_export.status = 'exporting'
    machine_export.save()

    (orig_managerCls, orig_creds, dest_managerCls) = \
        machine_export.prepare_manager()
    export_args = machine_export.get_export_args()
    #export_task = migrate_instance_task.si(
    #        orig_managerCls, orig_creds, dest_managerCls, orig_creds,
    #        **export_args)
    export_image_location = migrate_instance_task(orig_managerCls, orig_creds, dest_managerCls, orig_creds, **export_args)
    process_export(export_image_location, machine_export.id)

    #export_error_task = machine_export_error.s(machine_export.id)
    #export_task.link_error(export_error_task)
    #process_task = process_export.s(machine_export.id)
    #process_task.link_error(export_error_task)
    #export_task.link(process_task)
    ## Start the task.
    #async = export_task.apply_async()
    #if delay:
    #    async.get()
    #return async

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
    admin_driver = machine_request.new_admin_driver()
    admin_ident = machine_request.new_admin_identity()

    imaging_error_task = machine_request_error.s(machine_request.id)

    init_task = None

    if dest_managerCls and dest_creds != orig_creds:
        #Task 1 = Migrate Task
        migrate_task = migrate_instance_task.si(
            orig_managerCls, orig_creds, dest_managerCls, dest_creds,
            **imaging_args)
        if not init_task:
            init_task = migrate_task
        else:
            init_task.link(migrate_task)
    else:
        #Task 1 = Imaging Task
        image_task = machine_imaging_task.si(
            orig_managerCls, orig_creds, imaging_args)
        if not init_task:
            init_task = image_task
        else:
            init_task.link(image_task)
    #Task 2 = Process the machine request
    # (Save tags, name, description, metadata, etc.)
    process_task = process_request.s(machine_request.id)
    process_task.link_error(imaging_error_task)

    if dest_managerCls and dest_creds != orig_creds:
        migrate_task.link(process_task)
        migrate_task.link_error(imaging_error_task)
    else:
        image_task.link(process_task)
        image_task.link_error(imaging_error_task)
    #Task 3 = Validate the new image by launching an instance
    validate_task = validate_new_image.s(machine_request.id)
    process_task.link(validate_task)
    #Task 4 = Wait for new instance to be 'active'
    wait_for_task = wait_for.s(
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
    email_task = imaging_complete.s(machine_request.id)
    destroy_task.link_error(imaging_error_task)
    destroy_task.link(email_task)

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

@task(name='process_export', queue="imaging", ignore_result=False)
def process_export(export_file_path, machine_export_id):
    #if ipdb:
    #    ipdb.set_trace()
    machine_export = MachineExport.objects.get(id=machine_export_id)
    machine_export.status = 'completed'
    machine_export.export_file = export_file_path
    machine_export.end_date = timezone.now()
    machine_export.save()

    #send_image_export_email(machine_export.new_machine_owner,
    #                         machine_export.new_machine,
    #                         machine_export.new_machine_name)
    return export_file_path

@task(name='machine_export_error')
def machine_export_error(task_uuid, machine_export_id):
    logger.info("machine_export_id=%s" % machine_export_id)
    logger.info("task_uuid=%s" % task_uuid)

    result = app.AsyncResult(task_uuid)
    with allow_join_result():
        exc = result.get(propagate=False)
    err_str = "ERROR - %r Exception:%r" % (result.result, result.traceback,)
    logger.error(err_str)
    machine_export = MachineExport.objects.get(id=machine_export_id)
    machine_export.status = err_str
    machine_export.save()


@task(name='machine_request_error')
def machine_request_error(task_uuid, machine_request_id):
    logger.info("machine_request_id=%s" % machine_request_id)
    logger.info("task_uuid=%s" % task_uuid)

    result = app.AsyncResult(task_uuid)
    with allow_join_result():
        exc = result.get(propagate=False)
    err_str = "ERROR - %r Exception:%r" % (result.result, result.traceback,)
    logger.error(err_str)
    send_image_request_failed_email(machine_request, err_str)
    machine_request = MachineRequest.objects.get(id=machine_request_id)
    machine_request.status = err_str
    machine_request.save()


@task(name='imaging_complete', queue="imaging", ignore_result=False)
def imaging_complete(new_image_id, machine_request_id):
    #if ipdb:
    #    ipdb.set_trace()
    machine_request = MachineRequest.objects.get(id=machine_request_id)
    machine_request.status = 'completed'
    machine_request.save()
    send_image_request_email(machine_request.new_machine_owner,
                             machine_request.new_machine,
                             machine_request.new_machine_name)
    return new_image_id

@task(name='process_request', queue="imaging", ignore_result=False)
def process_request(new_image_id, machine_request_id):
    #if ipdb:
    #    ipdb.set_trace()
    machine_request = MachineRequest.objects.get(id=machine_request_id)
    machine_request.status = 'processing - %s' % new_image_id
    machine_request.save()
    invalidate_machine_cache(machine_request)

    #NOTE: This is taken care of indirectly by process_machine_request
    # and more directly by core/application.py:save_app_data
    #set_machine_request_metadata(machine_request, new_image_id)

    process_machine_request(machine_request, new_image_id)
    send_image_request_email(machine_request.new_machine_owner,
                             machine_request.new_machine,
                             machine_request.new_machine_name)
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
    #Update the admin driver's User (Cannot be initialized via. Chromogenic)
    admin_driver.identity.user = admin_ident.created_by
    #Update metadata on rtwo/libcloud machine -- NOT a glance machine
    machine = admin_driver.get_machine(image_id)
    small_size = admin_driver.list_sizes()[0]
    (instance_id, token, password) = launch_esh_instance(
            admin_driver,
            machine.id,
            small_size.id,
            admin_ident,
            'Automated Image Verification - %s' % image_id,
            'atmoadmin',
            using_admin=True)
    return instance_id


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
