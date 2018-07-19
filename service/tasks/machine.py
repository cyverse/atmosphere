from django.utils import timezone
from django.conf import settings
from threepio import celery_logger, logger

from celery.decorators import task
from celery.result import allow_join_result

from chromogenic.export import export_source
from chromogenic.tasks import machine_imaging_task, migrate_instance_task

from atmosphere.celery_init import app
from libcloud.common.exceptions import BaseHTTPError
from core.email import \
    send_image_request_email, send_image_request_failed_email
from core.models.machine_request import MachineRequest
from core.models.export_request import ExportRequest
from core.models.identity import Identity
from core.models.status_type import StatusType

from service.deploy import (
    build_host_name, deploy_prepare_snapshot,
    execution_has_failures, execution_has_unreachable)
from service.driver import get_admin_driver, get_esh_driver, get_account_driver
from service.machine import process_machine_request, add_membership, remove_membership
from service.tasks.driver import wait_for_instance, destroy_instance

@task(name="remove_membership_task",
      default_retry_delay=5,
      max_retries=2)
def remove_membership_task(image_version, group):
    celery_logger.debug("remove_membership_task task started at %s." % timezone.now())
    try:
        remove_membership(image_version, group)
        celery_logger.debug("remove_membership_task task finished at %s." % timezone.now())
    except Exception as exc:
        celery_logger.exception(exc)
        remove_membership_task.retry(exc=exc)


@task(name="add_membership_task",
      default_retry_delay=5,
      max_retries=2)
def add_membership_task(image_version, group):
    celery_logger.debug("add_membership_task task started at %s." % timezone.now())
    try:
        add_membership(image_version, group)
        celery_logger.debug("add_membership_task task finished at %s." % timezone.now())
    except Exception as exc:
        celery_logger.exception(exc)
        add_membership_task.retry(exc=exc)


def _get_imaging_task(orig_managerCls, orig_creds,
                      dest_managerCls, dest_creds, imaging_args):
    # NOTE: destManagerCls may == origManagerCls,
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


@task(name='export_request_task', queue="imaging", ignore_result=False)
def export_request_task(export_request_id):
    celery_logger.info("export_request_task task started at %s." % timezone.now())
    export_request = ExportRequest.objects.get(id=export_request_id)
    export_request.status = 'processing'
    export_request.save()

    (orig_managerCls, orig_creds) = export_request.prepare_manager()
    default_kwargs = export_request.get_export_args()
    file_loc = export_source(orig_managerCls, orig_creds, default_kwargs)

    celery_logger.info("export_request_task task finished at %s." % timezone.now())
    return file_loc


def start_export_request(export_request, delay=False):
    """
    Build up a machine export task using core.models.export_request
    """
    export_request.status = 'exporting'
    export_request.save()
    if delay:
        file_location = export_request_task(export_request.id)
        file_location = process_export(file_location, export_request.id)
        return file_location

    export_task = export_request_task.s(export_request.id)
    process_task = process_export.s(export_request.id)

    export_task.link(process_task)

    export_error_task = export_request_error.s(export_request.id)
    export_task.link_error(export_error_task)
    process_task.link_error(export_error_task)

    async = export_task.apply_async()
    if delay:
        async.get()
    return async


def start_machine_imaging(machine_request, delay=False):
    """
    Builds up a machine imaging task using core.models.machine_request
    delay - If true, wait until task is completed before returning
    """
    new_status, _ = StatusType.objects.get_or_create(name="started")
    machine_request.status = new_status
    machine_request.save()

    original_status = machine_request.old_status
    last_run_error, original_status = machine_request._recover_from_error(original_status)

    if last_run_error:
        machine_request.old_status = original_status
        machine_request.save()
    instance_id = machine_request.instance.provider_alias
    identity_id = machine_request.instance.created_by_identity_id

    (orig_managerCls, orig_creds,
     dest_managerCls, dest_creds) = machine_request.prepare_manager()
    imaging_args = machine_request.get_imaging_args()


    # NOTE: si == (Immutable Subtask) Ignore the result of the last task, all arguments must be passed into these tasks during creation step.
    # NOTE: s == (Subtask) Will use the result of last task as the _first argument_, arguments passed in will start from arg[1]
    imaging_error_task = machine_request_error.s(machine_request.id)

    # Task 1 - prepare the instance
    prep_instance_task = prep_instance_for_snapshot.si(identity_id, instance_id)

    # Task 2 = Imaging w/ Chromogenic
    imaging_task = _get_imaging_task(orig_managerCls, orig_creds,
                                     dest_managerCls, dest_creds,
                                     imaging_args)
    prep_instance_task.link(imaging_task)
    imaging_task.link_error(imaging_error_task)
    # Assume we are starting from the beginning.
    init_task = prep_instance_task
    # Task 3 = Process the machine request
    if 'processing - ' in original_status:
        # If processing, start here..
        image_id = original_status.replace("processing - ", "")
        logger.info("Start with processing:%s" % image_id)
        process_task = process_request.s(image_id, machine_request.id)
        init_task = process_task
    else:
        # Link from imaging to process..
        process_task = process_request.s(machine_request.id)
        imaging_task.link(process_task)
    process_task.link_error(imaging_error_task)

    # Task 4 (Optional) - Validate the image by launching a new instance
    # To skip, set ENABLE_IMAGE_VALIDATION to False

    # Final Task - email the user that their image is ready
    email_task = imaging_complete.si(machine_request.id)
    email_task.link_error(imaging_error_task)
    if getattr(settings, 'ENABLE_IMAGE_VALIDATION', True):
        init_task = enable_image_validation(machine_request, init_task, email_task, original_status, imaging_error_task)
    elif 'validating' == original_status:  # Imaging is complete if ENABLE_IMAGE_VALIDATION is false
        init_task = email_task
    else:
        process_task.link(email_task)

    # Set status to imaging ONLY if our initial task is the imaging task.
    if init_task == imaging_task:
        machine_request.old_status = 'imaging'
        machine_request.save()
    async = init_task.apply_async()
    if delay:
        async.get()
    return async


def enable_image_validation(machine_request, init_task, final_task, original_status="", error_handler_task=None):
    if not error_handler_task:
        error_handler_task = machine_request_error.s(machine_request.id)
    # Task 3 = Validate the new image by launching an instance
    admin_ident = machine_request.new_admin_identity()
    admin_driver = get_admin_driver(machine_request.new_machine_provider)
    if 'validating' == original_status:
        image_id = machine_request.new_machine.identifier
        celery_logger.info("Start with validating:%s" % image_id)
        # If validating, seed the image_id and start here..
        validate_task = validate_new_image.s(image_id, machine_request.id)
        init_task = validate_task
    else:
        validate_task = validate_new_image.s(machine_request.id)
        init_task.link(validate_task)
    # Task 4 = Terminate the new instance on completion
    destroy_task = destroy_instance_once_active.s(
        admin_driver.__class__,
        admin_driver.provider,
        admin_driver.identity,
        admin_ident.created_by,
        admin_ident.uuid)
    validate_task.link(destroy_task)
    validate_task.link_error(error_handler_task)
    destroy_task.link_error(error_handler_task)
    destroy_task.link(final_task)
    return init_task

@task(name="destroy_instance_once_active")
def destroy_instance_once_active(
        instance_alias,
        driverCls,
        provider,
        identity,
        admin_user,
        admin_ident_uuid):
    # This is a hacky method to chain two different tasks together. In this way
    # destroy_instance_once_active is really two separate tasks. We cannot use
    # the typical linking/chaining because, destroy_instance must follow
    # wait_for_task, and the instance_alias is only provided by a prior task
    wait_for_task = wait_for_instance.si(
        instance_alias,
        driverCls,
        provider,
        identity,
        "active")
    destroy_task = destroy_instance.si(
        instance_alias, admin_user, admin_ident_uuid)
    return (wait_for_task | destroy_task).delay().get()

def set_machine_request_metadata(machine_request, image_id):
    admin_driver = get_admin_driver(machine_request.new_machine_provider)
    machine = admin_driver.get_machine(image_id)
    lc_driver = admin_driver._connection
    if not machine:
        celery_logger.warn("Could not find machine with ID=%s" % image_id)
        return
    if not hasattr(lc_driver, 'ex_set_image_metadata'):
        return
    metadata = lc_driver.ex_get_image_metadata(machine)

    if machine_request.new_application_description:
        metadata['description'] = machine_request.new_application_description
    if machine_request.new_version_tags:
        metadata['tags'] = machine_request.new_version_tags
    celery_logger.info("LC Driver:%s - Machine:%s - Metadata:%s"
                % (lc_driver, machine.id, metadata))
    lc_driver.ex_set_image_metadata(machine, metadata)
    return machine


@task(name='process_export', queue="imaging", ignore_result=False)
def process_export(export_file_path, export_request_id):
    export_request = ExportRequest.objects.get(id=export_request_id)
    export_request.complete_export(export_file_path)
    # send_image_export_email(export_request.new_machine_owner,
    #                         export_request.new_machine,
    #                         export_request.new_application_name)
    return export_file_path


@task(name='export_request_error')
def export_request_error(task_uuid, export_request_id):
    celery_logger.info("export_request_id=%s" % export_request_id)
    celery_logger.info("task_uuid=%s" % task_uuid)

    result = app.AsyncResult(task_uuid)
    with allow_join_result():
        exc = result.get(propagate=False)
    err_str = "ERROR - %r Exception:%r" % (result.result, result.traceback,)
    celery_logger.error(err_str)
    export_request = ExportRequest.objects.get(id=export_request_id)
    export_request.status = err_str
    export_request.save()
def _status_to_error(old_status, error_title, error_traceback):
    # Don't prefix if request is already within the ()s
    if all(char in old_status for char in "()"):
        err_prefix = old_status
    else:
        err_prefix = "(%s)" % old_status
    err_str = "%s - ERROR - %r Exception:%r" % (err_prefix,
                                                error_title,
                                                error_traceback
                                                )
    return err_str

@task(name='machine_request_error')
def machine_request_error(task_request, *args, **kwargs):
    #Args format: (exception, ?, subtask_args...)
    exception = args[0]
    machine_request_id = args[2]
    task_uuid = task_request.id
    celery_logger.info("machine_request_id=%s" % machine_request_id)
    celery_logger.info("task_uuid=%s" % (task_uuid,) )
    celery_logger.info("exception=%s" % (exception,) )
    celery_logger.info("task_kwargs=%s" % kwargs)
    machine_request = MachineRequest.objects.get(id=machine_request_id)

    result = app.AsyncResult(task_uuid)
    with allow_join_result():
        exc = result.get(propagate=False)
    err_str = _status_to_error(machine_request.old_status, result.result, result.traceback)
    celery_logger.info("traceback=%s" % (result.traceback,) )
    celery_logger.error(err_str)
    machine_request = MachineRequest.objects.get(id=machine_request_id)
    machine_request.old_status = err_str
    machine_request.save()
    send_image_request_failed_email(machine_request, err_str)


@task(name='imaging_complete', ignore_result=False)
def imaging_complete(machine_request_id):
    machine_request = MachineRequest.objects.get(id=machine_request_id)
    machine_request.old_status = 'completed'
    new_status, _ = StatusType.objects.get_or_create(name="completed")
    machine_request.status = new_status
    machine_request.end_date = timezone.now()
    machine_request.save()
    send_image_request_email(machine_request.new_machine_owner,
                             machine_request.new_machine,
                             machine_request.new_application_name)
    new_image_id = machine_request.new_machine.identifier
    return new_image_id


@task(name='process_request', ignore_result=False)
def process_request(new_image_id, machine_request_id):
    """
    First, save the new image id so we can resume in case of failure.
    Then, Invalidate the machine cache to avoid a cache miss.
    Then, process the request by creating/updating all core objects related
    to this specific machine request.
    Finally, update the metadata on the provider.
    """
    machine_request = MachineRequest.objects.get(id=machine_request_id)
    new_status, _ = StatusType.objects.get_or_create(name="processing")
    machine_request.status = new_status
    machine_request.old_status = 'processing - %s' % new_image_id
    # HACK - TODO - replace with proper `default` in model
    # PATCHED (lenards, 2015-12-21)
    if machine_request.new_version_name is None:
        machine_request.new_version_name = "1.0"
    machine_request.save()
    # TODO: Best if we could 'broadcast' this to all running
    # Apache WSGI procs && celery 'imaging' procs
    process_machine_request(machine_request, new_image_id)
    return new_image_id


@task(name='validate_new_image', queue="imaging", ignore_result=False)
def validate_new_image(image_id, machine_request_id):
    if not getattr(settings, 'ENABLE_IMAGE_VALIDATION', True):
        celery_logger.warn(
            "Skip validation: ENABLE_IMAGE_VALIDATION is False")
        return True
    machine_request = MachineRequest.objects.get(id=machine_request_id)
    new_status, _ = StatusType.objects.get_or_create(name="validating")
    machine_request.status = new_status
    machine_request.old_status = 'validating'
    local_username = machine_request.created_by.username  #NOTE: Change local_username accordingly when this assumption is no longer true.
    machine_request.save()
    accounts = get_account_driver(machine_request.new_machine.provider)
    accounts.clear_cache()
    from service.instance import launch_machine_instance
    admin_driver = accounts.admin_driver
    admin_ident = machine_request.new_admin_identity()
    if not admin_driver:
        celery_logger.warn(
            "Need admin_driver functionality to auto-validate instance")
        return False
    if not admin_ident:
        celery_logger.warn(
            "Need to know the AccountProvider to auto-validate instance")
        return False
    # Attempt to launch using the admin_driver
    user = admin_ident.created_by
    admin_driver.identity.user = user
    machine = admin_driver.get_machine(image_id)
    sorted_sizes = admin_driver.list_sizes()
    size_index = 0
    while size_index < len(sorted_sizes):
        selected_size = sorted_sizes[size_index]
        size_index += 1
        try:
            instance = launch_machine_instance(
                admin_driver, user, admin_ident,
                machine, selected_size,
                'Automated Image Verification - %s' % image_id,
                username=local_username,
                using_admin=True)
            return instance.provider_alias
        except BaseHTTPError as http_error:
            if "Flavor's disk is too small for requested image" in http_error.message:
                continue
            logger.exception(http_error)
            raise
        except Exception as exc:
            logger.exception(exc)
            raise
    # End of while loop
    raise Exception("Validation of new Image %s has *FAILED*" % image_id)


@task(name='prep_instance_for_snapshot', ignore_result=False)
def prep_instance_for_snapshot(identity_id, instance_id, **celery_task_args):
    identity = Identity.objects.get(id=identity_id)
    try:
        celery_logger.debug("prep_instance_for_snapshot task started at %s." % timezone.now())
        # NOTE: FIXMEIF the assumption that the 'linux username'
        # is the 'created_by' AtmosphereUser changes.
        username = identity.created_by.username
        driver = get_esh_driver(identity)
        instance = driver.get_instance(instance_id)
        if instance.extra.get('status','') != 'active':
            celery_logger.info("prep_instance_for_snapshot skipped")
            return
        playbooks = deploy_prepare_snapshot(
            instance.ip, username, instance_id)
        celery_logger.info(playbooks.__dict__)
        hostname = build_host_name(instance.id, instance.ip)
        result = False if execution_has_failures(playbooks, hostname)\
            or execution_has_unreachable(playbooks, hostname) else True
        if not result:
            raise Exception(
                "Error encountered while preparing instance for snapshot: %s"
                % playbooks.stats.summarize(host=hostname))
    except Exception as exc:
        celery_logger.warn(exc)
        prep_instance_for_snapshot.retry(exc=exc)
