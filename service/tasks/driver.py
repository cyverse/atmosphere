"""
Tasks for driver operations.
NOTE: At this point create options do not have a hard-set requirement for 'CoreIdentity'
Delete/remove operations do. This should be investigated further..
"""
from operator import attrgetter
import sys
import re
import time

from django.conf import settings
from django.utils.timezone import datetime, timedelta
from celery.decorators import task
from celery.task import current
from celery.result import allow_join_result

from rtwo.exceptions import LibcloudDeploymentError

#TODO: Internalize exception into RTwo
from rtwo.exceptions import NonZeroDeploymentException, NeutronBadRequest
from neutronclient.common.exceptions import IpAddressGenerationFailureClient

from threepio import celery_logger, status_logger, logger

from celery import current_app as app

from core.email import send_instance_email
from core.models.boot_script import get_scripts_for_instance
from core.models.instance import Instance
from core.models.identity import Identity
from core.models.profile import UserProfile

from service.deploy import (
    inject_env_script, check_process, wrap_script,
    instance_deploy, user_deploy,
    build_host_name,
    ready_to_deploy as ansible_ready_to_deploy,
    run_utility_playbooks, execution_has_failures, execution_has_unreachable
    )
from service.driver import get_driver, get_account_driver
from service.exceptions import AnsibleDeployException
from service.instance import _update_instance_metadata
from service.networking import _generate_ssh_kwargs


def _update_status_log(instance, status_update):
    now_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        user = instance._node.extra['metadata']['creator']
    except KeyError as no_user:
        user = "Unknown -- Metadata missing"
    size_alias = instance._node.extra['flavorId']
    machine_alias = instance._node.extra['imageId']
    status_logger.debug("%s,%s,%s,%s,%s,%s"
                        % (now_time, user, instance.alias, machine_alias,
                           size_alias, status_update))


@task(name="print_debug")
def print_debug():
    log_str = "print_debug task finished at %s." % datetime.now()
    print log_str
    celery_logger.debug(log_str)


@task(name="complete_resize", max_retries=2, default_retry_delay=15)
def complete_resize(driverCls, provider, identity, instance_alias,
                    core_provider_uuid, core_identity_uuid, user):
    """
    Confirm the resize of 'instance_alias'
    """
    from service import instance as instance_service
    try:
        celery_logger.debug("complete_resize task started at %s." % datetime.now())
        driver = get_driver(driverCls, provider, identity)
        instance = driver.get_instance(instance_alias)
        if not instance:
            celery_logger.debug("Instance has been teminated: %s." % instance_id)
            return False, None
        result = instance_service.confirm_resize(
            driver, instance, core_provider_uuid, core_identity_uuid, user)
        celery_logger.debug("complete_resize task finished at %s." % datetime.now())
        return True, result
    except Exception as exc:
        celery_logger.exception(exc)
        complete_resize.retry(exc=exc)


@task(name="wait_for_instance", max_retries=250, default_retry_delay=15)
def wait_for_instance(
        instance_alias,
        driverCls,
        provider,
        identity,
        status_query,
        tasks_allowed=False,
        return_id=False,
        **task_kwargs):
    """
    #Task makes 250 attempts to 'look at' the instance, waiting 15sec each try
    Cumulative time == 1 hour 2 minutes 30 seconds before FAILURE

    status_query = "active" Match only one value, active
    status_query = ["active","suspended"] or match multiple values.
    """
    try:
        celery_logger.debug("wait_for task started at %s." % datetime.now())
        if app.conf.CELERY_ALWAYS_EAGER:
            celery_logger.debug("Eager task - DO NOT return until its ready!")
            return _eager_override(wait_for_instance, _is_instance_ready,
                                   (driverCls, provider, identity,
                                    instance_alias, status_query,
                                    tasks_allowed, return_id), {})

        result = _is_instance_ready(driverCls, provider, identity,
                                    instance_alias, status_query,
                                    tasks_allowed, return_id)
        return result
    except Exception as exc:
        if "Not Ready" not in str(exc):
            # Ignore 'normal' errors.
            celery_logger.exception(exc)

        wait_for_instance.retry(exc=exc)


def _eager_override(task_class, run_method, args, kwargs):
    attempts = 0
    delay = task_class.default_retry_delay or 30  # Seconds
    while attempts < task_class.max_retries:
        try:
            result = run_method(*args, **kwargs)
            return result
        except Exception as exc:
            celery_logger.exception("Encountered error while running eager")
        attempts += 1
        celery_logger.info("Waiting %d seconds" % delay)
        time.sleep(delay)
    return None


def _is_instance_ready(driverCls, provider, identity,
                       instance_alias, status_query,
                       tasks_allowed=False, return_id=False):
    # TODO: Refactor so that terminal states can be found. IE if waiting for
    # 'active' and in status: Suspended - none - GIVE up!!
    driver = get_driver(driverCls, provider, identity)
    instance = driver.get_instance(instance_alias)
    if not instance:
        celery_logger.debug("Instance has been terminated: %s." % instance_alias)
        if return_id:
            return None
        return False
    i_status = instance._node.extra['status'].lower()
    i_task = instance._node.extra['task']
    if (i_status not in status_query) or (i_task and not tasks_allowed):
        raise Exception(
            "Instance: %s: Status: (%s - %s) - Not Ready"
            % (instance.id, i_status, i_task))
    celery_logger.debug("Instance %s: Status: (%s - %s) - Ready"
                 % (instance.id, i_status, i_task))
    if return_id:
        return instance.id
    return True


@task(name="add_fixed_ip",
      ignore_result=True,
      default_retry_delay=15,
      max_retries=15)
def add_fixed_ip(
        driverCls,
        provider,
        identity,
        instance_id,
        core_identity_uuid=None):
    from service import instance as instance_service
    try:
        celery_logger.debug("add_fixed_ip task started at %s." % datetime.now())
        driver = get_driver(driverCls, provider, identity)
        instance = driver.get_instance(instance_id)
        if not instance:
            celery_logger.debug("Instance has been teminated: %s." % instance_id)
            return None
        if instance._node.private_ips:
            # TODO: Attempt to rescue
            celery_logger.info("Instance has fixed IP: %s" % instance_id)
            return instance

        network_id = instance_service._get_network_id(driver, instance)
        fixed_ip = driver._connection.ex_add_fixed_ip(instance, network_id)
        celery_logger.debug("add_fixed_ip task finished at %s." % datetime.now())
        return fixed_ip
    except Exception as exc:
        if "Not Ready" not in str(exc):
            # Ignore 'normal' errors.
            celery_logger.exception(exc)
        add_fixed_ip.retry(exc=exc)


def current_openstack_identities():
    identities = Identity.objects.filter(
        provider__type__name__iexact='openstack',
        provider__active=True)
    key_sorter = lambda ident: attrgetter(
        ident.provider.type.name,
        ident.created_by.username)
    identities = sorted(
        identities,
        key=key_sorter)
    return identities


def _remove_extra_floating_ips(driver, tenant_name):
    num_ips_removed = driver._clean_floating_ip()
    if num_ips_removed:
        celery_logger.debug("Removed %s ips from OpenStack Tenant %s"
                     % (num_ips_removed, tenant_name))
    return num_ips_removed


def _remove_ips_from_inactive_instances(driver, instances):
    from service import instance as instance_service
    for instance in instances:
        # DOUBLE-CHECK:
        if driver._is_inactive_instance(instance) and instance.ip:
            # If an inactive instance has floating/fixed IPs.. Remove them!
            instance_service.remove_ips(driver, instance)
    return True


def _remove_network(
        os_acct_driver,
        core_identity,
        tenant_name):
    """
    """
    celery_logger.info("Removing project network for %s" % tenant_name)
    # Sec. group can't be deleted if instances are suspended
    # when instances are suspended we pass remove_network=False
    os_acct_driver.delete_security_group(core_identity)
    os_acct_driver.delete_user_network(core_identity)
    return True


@task(name="clear_empty_ips_for")
def clear_empty_ips_for(core_identity_uuid, username=None):
    """
    RETURN: (number_ips_removed, delete_network_called)
    """
    from service.driver import get_esh_driver
    from rtwo.driver import OSDriver
    # Initialize the drivers
    core_identity = Identity.objects.get(uuid=core_identity_uuid)
    driver = get_esh_driver(core_identity)
    if not isinstance(driver, OSDriver):
        return (0, False)
    os_acct_driver = get_account_driver(core_identity.provider)
    celery_logger.info("Initialized account driver")
    # Get useful info
    creds = core_identity.get_credentials()
    tenant_name = creds['ex_tenant_name']
    celery_logger.info("Checking Identity %s" % tenant_name)
    # Attempt to clean floating IPs
    num_ips_removed = _remove_extra_floating_ips(driver, tenant_name)
    # Test for active/inactive_instances instances
    instances = driver.list_instances()
    # Active True IFF ANY instance is 'active'
    active_instances = any(driver._is_active_instance(inst)
                           for inst in instances)
    # Inactive True IFF ALL instances are suspended/stopped
    inactive_instances = all(driver._is_inactive_instance(inst)
                             for inst in instances)
    _remove_ips_from_inactive_instances(driver, instances)
    if active_instances and not inactive_instances:
        # User has >1 active instances AND not all instances inactive_instances
        return (num_ips_removed, False)
    network_id = os_acct_driver.network_manager.get_network_id(
        os_acct_driver.network_manager.neutron,
        '%s-net' % tenant_name)
    if network_id:
        # User has 0 active instances OR all instances are inactive_instances
        # Network exists, attempt to dismantle as much as possible
        # Remove network=False IFF inactive_instances=True..
        remove_network = not inactive_instances
        if remove_network:
            _remove_network(
                os_acct_driver,
                core_identity,
                tenant_name)
            return (num_ips_removed, True)
        return (num_ips_removed, False)
    else:
        celery_logger.info("No Network found. Skipping %s" % tenant_name)
        return (num_ips_removed, False)


@task(name="clear_empty_ips")
def clear_empty_ips():
    celery_logger.debug("clear_empty_ips task started at %s." % datetime.now())
    if settings.DEBUG:
        celery_logger.debug("clear_empty_ips task SKIPPED at %s." % datetime.now())
        return
    identities = current_openstack_identities()
    for core_identity in identities:
        try:
            # TODO: Add some
            clear_empty_ips_for.apply_async(args=[core_identity.uuid,
                                                  core_identity.created_by])
        except Exception as exc:
            celery_logger.exception(exc)
    celery_logger.debug("clear_empty_ips task finished at %s." % datetime.now())


@task(name="_send_instance_email",
      default_retry_delay=10,
      max_retries=2)
def _send_instance_email(driverCls, provider, identity, instance_id):
    try:
        celery_logger.debug("_send_instance_email task started at %s." %
                     datetime.now())
        driver = get_driver(driverCls, provider, identity)
        instance = driver.get_instance(instance_id)
        # Breakout if instance has been deleted at this point
        if not instance:
            celery_logger.debug("Instance has been teminated: %s." % instance_id)
            return
        #FIXME: this is not a safe way to retrieve username. this is not a CoreIdentity.
        username = identity.user.username
        profile = UserProfile.objects.get(user__username=username)
        if profile.send_emails:
            # Only send emails if allowed by profile setting
            created = datetime.strptime(instance.extra['created'],
                                        "%Y-%m-%dT%H:%M:%SZ")
            send_instance_email(username,
                                instance.id,
                                instance.name,
                                instance.ip,
                                created,
                                username)
        else:
            celery_logger.debug("User %s elected NOT to receive new instance emails"
                         % username)

        celery_logger.debug("_send_instance_email task finished at %s." %
                     datetime.now())
    except (BaseException, Exception) as exc:
        celery_logger.warn(exc)
        _send_instance_email.retry(exc=exc)

def _send_instance_email_with_failure(driverCls, provider, identity, instance_id, username, error_message):
    driver = get_driver(driverCls, provider, identity)
    instance = driver.get_instance(instance_id)
    created = datetime.strptime(instance.extra['created'],
                                "%Y-%m-%dT%H:%M:%SZ")
    # Breakout if instance has been deleted at this point
    if not instance:
        celery_logger.debug("Instance has been teminated: %s." % instance_id)
        return
    #FIXME: this is not a safe way to retrieve username. this is not a CoreIdentity.
    send_instance_email(username,
                        instance.id,
                        instance.name,
                        instance.ip,
                        created,
                        username,
                        user_failure=True,
                        user_failure_message=error_message)

# Deploy and Destroy tasks
@task(name="user_deploy_failed")
def user_deploy_failed(
        task_uuid,
        driverCls,
        provider,
        identity,
        instance_id,
        user,
        message=None,
        **celery_task_args):
    try:
        celery_logger.debug("user_deploy_failed task started at %s." % datetime.now())
        if task_uuid:
            celery_logger.info("task_uuid=%s" % task_uuid)
            result = app.AsyncResult(task_uuid)
            with allow_join_result():
                exc = result.get(propagate=False)
            err_str = "Error Traceback:%s" % (result.traceback,)
            err_str = _cleanup_traceback(err_str)
        elif message:
            err_str = message
        else:
            err_str = "Deploy failed called externally. No matching AsyncResult"
        celery_logger.error(err_str)
        # Send deploy email
        _send_instance_email_with_failure(driverCls, provider, identity, instance_id, user.username, err_str)
	# Update metadata on the instance
        metadata={'tmp_status': 'user_deploy_error'}
        update_metadata.s(driverCls, provider, identity, instance_id,
                          metadata, replace_metadata=False).apply_async()
        celery_logger.debug("user_deploy_failed task finished at %s." % datetime.now())
        return err_str
    except Exception as exc:
        celery_logger.warn(exc)
        user_deploy_failed.retry(exc=exc)


@task(name="deploy_failed")
def deploy_failed(
        task_uuid,
        driverCls,
        provider,
        identity,
        instance_id,
        message=None,
        **celery_task_args):
    try:
        celery_logger.debug("deploy_failed task started at %s." % datetime.now())
        if task_uuid:
            celery_logger.info("task_uuid=%s" % task_uuid)
            result = app.AsyncResult(task_uuid)
            with allow_join_result():
                exc = result.get(propagate=False)
            err_str = "DEPLOYERROR::%s" % (result.traceback,)
        elif message:
            err_str = message
        else:
            err_str = "Deploy failed called externally. No matching AsyncResult"
        celery_logger.error(err_str)
        driver = get_driver(driverCls, provider, identity)
        instance = driver.get_instance(instance_id)

        metadata={'tmp_status': 'deploy_error'}
        update_metadata.s(driverCls, provider, identity, instance.id,
                          metadata, replace_metadata=False).apply_async()
        # Send deploy email
        celery_logger.debug("deploy_failed task finished at %s." % datetime.now())
    except Exception as exc:
        celery_logger.warn(exc)
        deploy_failed.retry(exc=exc)


@task(name="deploy_init_to",
      default_retry_delay=20,
      ignore_result=True,
      max_retries=3)
def deploy_init_to(driverCls, provider, identity, instance_id, core_identity,
                   username=None, password=None, redeploy=False, deploy=True,
                   *args, **kwargs):
    try:
        celery_logger.debug("deploy_init_to task started at %s." % datetime.now())
        celery_logger.debug("deploy_init_to deploy = %s" % deploy)
        celery_logger.debug("deploy_init_to type(deploy) = %s" % type(deploy))
        driver = get_driver(driverCls, provider, identity)
        instance = driver.get_instance(instance_id)
        if not instance:
            celery_logger.debug("Instance has been teminated: %s." % instance_id)
            return
        image_metadata = driver._connection\
                               .ex_get_image_metadata(instance.source)
        deploy_chain = get_deploy_chain(
            driverCls, provider, identity, instance, core_identity,
            username=username, password=password,
            redeploy=redeploy, deploy=deploy)
        celery_logger.debug(
            "Starting deploy chain 'ROUTE' @ Task: %s for: %s." %
            (deploy_chain, instance_id))
        if deploy_chain:
            deploy_chain.apply_async()
        # Can be really useful when testing.
        celery_logger.debug("deploy_init_to task finished at %s." % datetime.now())
    except SystemExit:
        celery_logger.exception("System Exits are BAD! Find this and get rid of it!")
        raise Exception("System Exit called")
    except NonZeroDeploymentException as non_zero:
        celery_logger.error(str(non_zero))
        celery_logger.error(non_zero.__dict__)
        raise
    except (BaseException, Exception) as exc:
        celery_logger.warn(exc)
        deploy_init_to.retry(exc=exc)


def get_deploy_chain(
        driverCls,
        provider,
        identity,
        instance,
        core_identity,
        username=None,
        password=None,
        redeploy=False,
        deploy=True):
    start_task = get_chain_from_build(
        driverCls, provider, identity, instance, core_identity,
        username=username, password=password, redeploy=redeploy, deploy=deploy)
    return start_task


def get_idempotent_deploy_chain(
        driverCls,
        provider,
        identity,
        instance,
        core_identity,
        username):
    """
    Takes an instance in ANY 'tmp_status' (Just launched or long-launched and recently started)
    and attempts to redeploy and complete the process!
    """
    metadata = instance.extra.get('metadata', {})
    instance_status = instance.extra.get('status', '').lower()
    start_task = None

    if not metadata or not instance_status:
        raise Exception(
            "This function cannot work without access to instance metadata AND status."
            " re-write this function to access the instance's metadata AND status!")
    tmp_status = metadata.get('tmp_status', '').lower()

    if instance_status in ['suspended', 'stopped', 'paused',
                           'shutoff', 'shelved', 'shelve_offload', 'error']:
        celery_logger.info(
            "Instance %s was contains an INACTIVE status: %s. Removing the tmp_status and allow 'traditional flows' to take place." %
            (instance.id, instance_status))
        start_task = get_remove_status_chain(
            driverCls,
            provider,
            identity,
            instance)
    elif tmp_status == 'initializing':
        celery_logger.info(
            "Instance %s contains the 'initializing' metadata - Redeploy will include wait_for_active AND networking AND deploy." %
            instance.id)
        start_task = get_chain_from_build(
            driverCls,
            provider,
            identity,
            instance,
            core_identity,
            username=username,
            redeploy=False)
    elif tmp_status == 'networking':
        celery_logger.info(
            "Instance %s contains the 'networking' metadata - Redeploy will include networking AND deploy." %
            instance.id)
        start_task = get_chain_from_active_no_ip(
            driverCls,
            provider,
            identity,
            instance,
            core_identity,
            username=username,
            redeploy=False)
    elif not instance.ip:
        celery_logger.info(
            "Instance %s is missing an IP address. - Redeploy will include networking AND deploy." %
            instance.id)
        start_task = get_chain_from_active_no_ip(
            driverCls,
            provider,
            identity,
            instance,
            core_identity,
            username=username,
            redeploy=False)
    elif tmp_status in ['deploying', 'deploy_error']:
        celery_logger.info(
            "Instance %s contains the 'deploying' metadata - Redeploy will include deploy ONLY!." %
            instance.id)
        start_task = get_chain_from_active_with_ip(
            driverCls,
            provider,
            identity,
            instance,
            core_identity,
            username=username,
            redeploy=False)
    else:
        raise Exception(
            "Instance has a tmp_status that is NOT: [initializing, networking, deploying] - %s" %
            tmp_status)
    return start_task


def get_remove_status_chain(driverCls, provider, identity, instance):
    if instance.extra['metadata'].get('iplant_suspend_fix'):
        replace = True
        final_update = instance.extra['metadata']
        final_update.pop('tmp_status')
        final_update.pop('iplant_suspend_fix')
    else:
        final_update = {'tmp_status': ''}
        replace = False
    remove_status_task = update_metadata.si(
        driverCls, provider, identity, instance.id,
        final_update, replace)
    start_chain = remove_status_task
    return start_chain


def get_chain_from_build(
        driverCls, provider, identity, instance, core_identity,
        username=None, password=None, redeploy=False, deploy=True):
    """
    Wait for instance to go to active.
    THEN Initialize the networking for the instance
    THEN deploy to the box.
    """
    wait_active_task = wait_for_instance.s(
        instance.id, driverCls, provider, identity, "active")
    start_chain = wait_active_task
    network_start = get_chain_from_active_no_ip(
        driverCls, provider, identity, instance, core_identity, username=username,
        password=password, redeploy=redeploy, deploy=deploy)
    start_chain.link(network_start)
    return start_chain


def print_chain(start_task, idx=0):
    #FINAL case
    count = idx + 1
    signature = "\n%s Task %s: %s(args=%s) " % ("  "*(idx), count, start_task.task, start_task.args)
    if not start_task.options.get('link'):
        mystr = '%s\n%s(FINAL TASK)' % (signature, "  "*(idx+1))
        return mystr
    #Recursive Case
    mystr = "%s" % signature
    next_tasks = start_task.options['link']
    for task in next_tasks:
        mystr += print_chain(task, idx+1)
    return mystr

def get_chain_from_active_no_ip(
        driverCls, provider, identity, instance, core_identity,
        username=None, password=None, redeploy=False, deploy=True):
    """
    Initialize the networking for the instance
    THEN deploy to the box.
    """
    start_chain = None
    end_chain = None
    # Init the networking
    celery_logger.debug("IP address missing -- add 'add floating IP' tasks..")
    network_meta_task = update_metadata.si(
        driverCls, provider, identity, instance.id,
        {'tmp_status': 'networking'})
    floating_task = add_floating_ip.si(
        driverCls, provider, identity, instance.id, delete_status=False)
    floating_task.link_error(
        deploy_failed.s(driverCls, provider, identity, instance.id))

    if instance.extra.get('metadata', {}).get('tmp_status', '') == 'networking':
        start_chain = floating_task
    else:
        start_chain = network_meta_task
        start_chain.link(floating_task)
    end_chain = floating_task
    deploy_start = get_chain_from_active_with_ip(
        driverCls, provider, identity, instance, core_identity,
        username=username, password=password,
        redeploy=redeploy, deploy=deploy)
    end_chain.link(deploy_start)
    return start_chain


def get_chain_from_active_with_ip(
        driverCls, provider, identity, instance, core_identity,
        username=None, password=None, redeploy=False, deploy=True):
    """
    Use Case: Instance has (or will be at start of this chain) an IP && is active.
    Goal: if 'Deploy' - Update metadata to inform you will be deploying
          else        - Remove metadata and end.
    """
    if redeploy:
        celery_logger.warn("WARNING: 'Redeploy' as an individual option is DEPRECATED, as 'ansible' is idempotent")
    start_chain = None
    # Guarantee 'networking' passes deploy_ready_test first!
    deploy_ready_task = deploy_ready_test.si(
        driverCls, provider, identity, instance.id)
    # ALWAYS start by testing that deployment is possible. then deploy.
    start_chain = deploy_ready_task

    # IMPORTANT NOTE: we are NOT updating to 'deploying' until actual
    # deployment takes place (SSH established. Time spent from
    # 'add_floating_ip' to SSH established is considered 'networking' time)
    if not deploy:
        remove_status_chain = get_remove_status_chain(
            driverCls,
            provider,
            identity,
            instance)
        deploy_ready_task.link(remove_status_chain)
        # Active and deployable. Ready for use!
        return start_chain

    # Start building a deploy chain
    deploy_meta_task = update_metadata.si(
        driverCls, provider, identity, instance.id,
        {'tmp_status': 'deploying'})

    deploy_task = _deploy_instance.si(
        driverCls, provider, identity, instance.id,
        username, None, redeploy)
    deploy_user_task = _deploy_instance_for_user.si(
        driverCls, provider, identity, instance.id,
        username, None, redeploy)
    check_vnc_task = check_process_task.si(
        driverCls, provider, identity, instance.id)
    check_web_desktop = check_web_desktop_task.si(
        driverCls, provider, identity, instance.id)
    remove_status_chain = get_remove_status_chain(
        driverCls,
        provider,
        identity,
        instance)
    remove_status_on_failure_task = get_remove_status_chain(
        driverCls,
        provider,
        identity,
        instance)
    user_deploy_failed_task = user_deploy_failed.s(
        driverCls, provider, identity, instance.id, core_identity.created_by)
    email_task = _send_instance_email.si(
        driverCls, provider, identity, instance.id)
    # JUST before we finish, check for boot_scripts_chain
    boot_chain_start, boot_chain_end = _get_boot_script_chain(
        driverCls, provider, identity, instance.id, core_identity)


    # (SUCCESS_)LINKS and ERROR_LINKS
    deploy_task.link_error(
        deploy_failed.s(driverCls, provider, identity, instance.id))
    deploy_user_task.link_error(user_deploy_failed_task)
    # Note created new 'copy' of remove_status to avoid potential for email*2
    user_deploy_failed_task.link(remove_status_on_failure_task)

    deploy_ready_task.link(deploy_meta_task)
    deploy_meta_task.link(deploy_task)
    deploy_task.link(check_web_desktop)
    check_web_desktop.link(check_vnc_task)  # Above this line, atmo is responsible for success.
    check_vnc_task.link(deploy_user_task)  # this line and below, user can create a failure.
    # ready -> metadata -> deployment..

    if boot_chain_start and boot_chain_end:
        # ..deployment -> scripts -> ..
        deploy_user_task.link(boot_chain_start)
        boot_chain_end.link(remove_status_chain)
    else:
        deploy_user_task.link(remove_status_chain)
    # Final task at this point should be 'remove_status_chain'

    # Only send emails when 'redeploy=False'
    if not redeploy:
        remove_status_chain.link(email_task)
    celery_logger.info("Deploy Chain : %s" % print_chain(start_chain, idx=0))
    return start_chain


@task(name="deploy_boot_script",
      default_retry_delay=32,
      time_limit=30 * 60,  # 30minute hard-set time limit.
      max_retries=10)
def deploy_boot_script(driverCls, provider, identity, instance_id,
                       script_text, script_name, **celery_task_args):
    """
    FIXME: how could we make this ansible-ized?
    """
    # Note: Splitting preperation (Of the MultiScriptDeployment) and execution
    # This makes it easier to output scripts for debugging of users.
    try:
        celery_logger.debug("deploy_boot_script task started at %s." % datetime.now())
        # Check if instance still exists
        driver = get_driver(driverCls, provider, identity)
        instance = driver.get_instance(instance_id)
        if not instance:
            celery_logger.debug("Instance has been teminated: %s." % instance_id)
            return
        # NOTE: This is required to use ssh to connect.
        # TODO: Is this still necessary? What about times when we want to use
        # the adminPass? --Steve
        celery_logger.info(instance.extra)
        instance._node.extra['password'] = None
        new_script = wrap_script(script_text, script_name)
    except (BaseException, Exception) as exc:
        celery_logger.exception(exc)
        deploy_boot_script.retry(exc=exc)

    try:
        kwargs = _generate_ssh_kwargs()
        kwargs.update({'deploy': new_script})
        driver.deploy_to(instance, **kwargs)
        _update_status_log(instance, "Deploy Finished")
        celery_logger.debug(
            "deploy_boot_script task finished at %s." %
            datetime.now())
    except LibcloudDeploymentError as exc:
        celery_logger.exception(exc)
        full_script_output = _parse_script_output(new_script)
        if isinstance(exc.value, NonZeroDeploymentException):
            # The deployment was successful, but the return code on one or more
            # steps is bad. Log the exception and do NOT try again!
            raise NonZeroDeploymentException,\
                "Boot Script reported a NonZeroDeployment:%s"\
                % full_script_output,\
                sys.exc_info()[2]
        # TODO: Check if all exceptions thrown at this time
        # fall in this category, and possibly don't retry if
        # you hit the Exception block below this.
        deploy_boot_script.retry(exc=exc)
    except (BaseException, Exception) as exc:
        celery_logger.exception(exc)
        deploy_boot_script.retry(exc=exc)


@task(name="boot_script_failed")
def boot_script_failed(task_uuid, driverCls, provider, identity, instance_id,
                       **celery_task_args):
    try:
        celery_logger.debug("boot_script_failed task started at %s." % datetime.now())
        celery_logger.info("task_uuid=%s" % task_uuid)
        result = app.AsyncResult(task_uuid)
        with allow_join_result():
            exc = result.get(propagate=False)
        err_str = "BOOT SCRIPT ERROR::%s" % (result.traceback,)
        celery_logger.error(err_str)
        driver = get_driver(driverCls, provider, identity)
        instance = driver.get_instance(instance_id)

        metadata={'tmp_status': 'boot_script_error'}
        update_metadata.s(driverCls, provider, identity, instance.id,
                          metadata, replace_metadata=False).apply_async()
        # TODO: Send 'boot script failed' email
        celery_logger.debug(
            "boot_script_failed task finished at %s." %
            datetime.now())
    except (BaseException, Exception) as exc:
        celery_logger.warn(exc)
        boot_script_failed.retry(exc=exc)


def _get_boot_script_chain(
        driverCls, provider, identity, instance_id,
        core_identity, remove_status=False):
    core_instance = Instance.objects.get(provider_alias=instance_id)
    scripts = get_scripts_for_instance(core_instance)
    first_task = end_task = None
    if not scripts:
        return first_task, end_task
    script_zero = deploy_boot_script.si(
            driverCls, provider, identity, instance_id,
            inject_env_script(core_identity.created_by.username),
            "Inject ENV variables")
    total = len(scripts)
    for idx, script in enumerate(scripts):
        # Name the status
        if total > 1:
            script_text = "running_boot_script: #%s/%s" % (idx + 1, total)
        else:
            script_text = "running_boot_script"
        # Update the status
        init_script_status_task = update_metadata.si(
            driverCls, provider, identity, instance_id,
            {'tmp_status': script_text})
        init_script_status_task.link_error(
            boot_script_failed.s(driverCls, provider, identity, instance_id))

        # Execute script
        deploy_script_task = deploy_boot_script.si(
            driverCls, provider, identity, instance_id,
            script.get_text(), script.get_title_slug())
        deploy_script_task.link_error(
            user_deploy_failed.s(driverCls, provider, identity, instance_id, core_identity.created_by))

        # Base case: First link
        if idx == 0:
            first_task = script_zero  # Always first
            script_zero.link(init_script_status_task)  # Link first script after it
            script_zero.link_error(
                boot_script_failed.s(driverCls, provider, identity, instance_id))
        else:
	    # All other links: Add init to end_task (a deploy)
            end_task.link(init_script_status_task)

        init_script_status_task.link(deploy_script_task)

        if idx == total - 1 and remove_status:
            # Actions are slightly different if this is the final task
            clear_script_status_task = update_metadata.si(
                driverCls, provider, identity, instance_id,
                {'tmp_status': ''})
            deploy_script_task.link(clear_script_status_task)
            clear_script_status_task.link_error(
                boot_script_failed.s(
                    driverCls,
                    provider,
                    identity,
                    instance_id))
            end_task = clear_script_status_task
        else:
            end_task = deploy_script_task
    return first_task, end_task


@task(name="destroy_instance",
      default_retry_delay=15,
      ignore_result=True,
      max_retries=3)
def destroy_instance(instance_alias, user, core_identity_uuid):
    """
    NOTE: Argument order changes here -- instance_alais is used as the first argument to make chaining this taks easier with celery.
    """
    from service import instance as instance_service
    try:
        celery_logger.debug("destroy_instance task started at %s." % datetime.now())
        core_instance = instance_service.destroy_instance(
            user, core_identity_uuid, instance_alias)
        celery_logger.debug("destroy_instance task finished at %s." % datetime.now())
        return core_instance
    except Exception as exc:
        celery_logger.exception(exc)
        destroy_instance.retry(exc=exc)


def _generate_stats(current_request, task_class):
    num_retries = current_request.retries
    remaining_retries = task_class.max_retries - num_retries
    delta_time = timedelta(
        seconds=num_retries *
        task_class.default_retry_delay)
    failure_eta = datetime.now() + delta_time
    return "Attempts made: %s (over %s) "\
        "Attempts Remaining: %s (ETA to Failure: %s)"\
        % (num_retries, delta_time, remaining_retries, failure_eta)


def _deploy_ready_failed_email_test(
        driver,
        instance_id,
        exc_message,
        current_request,
        task_class):
    """
    Additional Acitons Include:
    * 50% - Send an Email to atmosphere alerts to notify that there *may* be a problem
    #100% - Send an Email to atmosphere to notify that a deployment failed
    #       Terminate the current chain, and call 'deploy_failed' task out of band.
    """
    from core.email import send_preemptive_deploy_failed_email
    core_instance = Instance.objects.get(provider_alias=instance_id)
    num_retries = current_request.retries
    message = _generate_stats(current_request, task_class)

    if 'terminated' in str(exc_message):
        # Do NOTHING!
        pass
    elif num_retries == int(task_class.max_retries/2):
        # Halfway point. Send preemptive failure
        send_preemptive_deploy_failed_email(core_instance, message)
    elif num_retries == task_class.max_retries - 1:
        # Final attempt logic
        failure_task = deploy_failed.s(
            None,
            driver.__class__,
            driver.provider,
            driver.identity,
            instance_id,
            message=message)
        failure_task.apply_async()


@task(name="deploy_ready_test",
      default_retry_delay=64,
      # 16 second hard-set time limit. (NOTE:TOO LONG? -SG)
      soft_time_limit=120,
      max_retries=300  # Attempt up to two hours
      )
def deploy_ready_test(driverCls, provider, identity, instance_id,
                      **celery_task_args):
    """
    deploy_ready_test -
    Sends an "echo script" via SSH to the instance. If the script fails to
    deploy to the instance for any reason, log the exception and prepare to retry.

    Before making call to retry, send _deploy_ready_failed_email_test the
    current number of retries, max retries, etc. to see if additional action should be taken.
    """
    current_count = current.request.retries + 1
    total = deploy_ready_test.max_retries
    celery_logger.debug(
        "deploy_ready_test task %s/%s started at %s." %
        (current_count, total, datetime.now()))
    try:
        # Sanity checks -- get your ducks in a row.
        driver = get_driver(driverCls, provider, identity)
        instance = driver.get_instance(instance_id)
        if not instance:
            celery_logger.debug("Instance has been teminated: %s." % instance_id)
            raise Exception("Instance maybe terminated? "
                            "-- Going to keep trying anyway")
        if not instance.ip:
            celery_logger.debug("Instance IP address missing from : %s." % instance_id)
            raise Exception("Instance IP Missing? %s" % instance_id)

    except (BaseException, Exception) as exc:
        celery_logger.exception(exc)
        _deploy_ready_failed_email_test(
            driver, instance_id, exc.message, current.request, deploy_ready_test)
        deploy_ready_test.retry(exc=exc)
    # USE ANSIBLE
    try:
        username = identity.user.username
        playbooks = ansible_ready_to_deploy(instance.ip, username, instance_id)
        _update_status_log(instance, "Ansible Finished (ready test) for %s." % instance.ip)
        celery_logger.debug("deploy_ready_test task finished at %s." % datetime.now())
    except AnsibleDeployException as exc:
        deploy_ready_test.retry(exc=exc)
    except LibcloudDeploymentError as exc:
        celery_logger.exception(exc)
        full_deploy_output = _parse_steps_output(msd)
        if isinstance(exc.value, NonZeroDeploymentException):
            # The deployment was successful, but the return code on one or more
            # steps is bad. Log the exception and do NOT try again!
            raise NonZeroDeploymentException,\
                "One or more Script(s) reported a NonZeroDeployment:%s"\
                % full_deploy_output,\
                sys.exc_info()[2]
        # TODO: Check if all exceptions thrown at this time
        # fall in this category, and possibly don't retry if
        # you hit the Exception block below this.
        deploy_ready_test.retry(exc=exc)
    except (BaseException, Exception) as exc:
        celery_logger.exception(exc)
        deploy_ready_test.retry(exc=exc)


@task(name="_deploy_instance_for_user",
      default_retry_delay=32,
      time_limit=32 * 60,  # 32 minute hard-set time limit.
      max_retries=3
      )
def _deploy_instance_for_user(driverCls, provider, identity, instance_id,
                    username=None, password=None, token=None, redeploy=False,
                    **celery_task_args):
    # Note: Splitting preperation (Of the MultiScriptDeployment) and execution
    # This makes it easier to output scripts for debugging of users.
    try:
        celery_logger.debug("_deploy_instance_for_user task started at %s." % datetime.now())
        # Check if instance still exists
        driver = get_driver(driverCls, provider, identity)
        instance = driver.get_instance(instance_id)
        if not instance:
            celery_logger.debug("Instance has been teminated: %s." % instance_id)
            return
        if not instance.ip:
            celery_logger.debug("Instance IP address missing from : %s." % instance_id)
            raise Exception("Instance IP Missing? %s" % instance_id)
        # NOTE: This is required to use ssh to connect.
        # TODO: Is this still necessary? What about times when we want to use
        # the adminPass? --Steve
        celery_logger.info(instance.extra)
        instance._node.extra['password'] = None

    except (BaseException, Exception) as exc:
        celery_logger.exception(exc)
        _deploy_instance.retry(exc=exc)
    try:
        username = identity.user.username
        user_deploy(instance.ip, username, instance_id)
        _update_status_log(instance, "Ansible Finished for %s." % instance.ip)
        celery_logger.debug("_deploy_instance_for_user task finished at %s." % datetime.now())
    except AnsibleDeployException as exc:
        celery_logger.exception(exc)
        _deploy_instance_for_user.retry(exc=exc)
    except LibcloudDeploymentError as exc:
        celery_logger.exception(exc)
        full_deploy_output = _parse_steps_output(msd)
        if isinstance(exc.value, NonZeroDeploymentException):
            # The deployment was successful, but the return code on one or more
            # steps is bad. Log the exception and do NOT try again!
            raise NonZeroDeploymentException,\
                "One or more Script(s) reported a NonZeroDeployment:%s"\
                % full_deploy_output,\
                sys.exc_info()[2]
        # TODO: Check if all exceptions thrown at this time
        # fall in this category, and possibly don't retry if
        # you hit the Exception block below this.
        _deploy_instance_for_user.retry(exc=exc)
    except (BaseException, Exception) as exc:
        celery_logger.exception(exc)
        _deploy_instance_for_user.retry(exc=exc)




@task(name="_deploy_instance",
      default_retry_delay=124,
      soft_time_limit=32 * 60,  # 32 minute hard-set time limit.
      max_retries=10
      )
def _deploy_instance(driverCls, provider, identity, instance_id,
                    username=None, password=None, token=None, redeploy=False,
                    **celery_task_args):
    # Note: Splitting preperation (Of the MultiScriptDeployment) and execution
    # This makes it easier to output scripts for debugging of users.
    try:
        celery_logger.debug("_deploy_instance task started at %s." % datetime.now())
        # Check if instance still exists
        driver = get_driver(driverCls, provider, identity)
        instance = driver.get_instance(instance_id)
        if not instance:
            celery_logger.debug("Instance has been teminated: %s." % instance_id)
            return
        if not instance.ip:
            celery_logger.debug("Instance IP address missing from : %s." % instance_id)
            raise Exception("Instance IP Missing? %s" % instance_id)
        # NOTE: This is required to use ssh to connect.
        # TODO: Is this still necessary? What about times when we want to use
        # the adminPass? --Steve
        celery_logger.info(instance.extra)
        instance._node.extra['password'] = None

    except (BaseException, Exception) as exc:
        celery_logger.exception(exc)
        _deploy_instance.retry(exc=exc)
    try:
        username = identity.user.username
        instance_deploy(instance.ip, username, instance_id)
        _update_status_log(instance, "Ansible Finished for %s." % instance.ip)
        celery_logger.debug("_deploy_instance task finished at %s." % datetime.now())
    except AnsibleDeployException as exc:
        celery_logger.exception(exc)
        _deploy_instance.retry(exc=exc)
    except LibcloudDeploymentError as exc:
        celery_logger.exception(exc)
        full_deploy_output = _parse_steps_output(msd)
        if isinstance(exc.value, NonZeroDeploymentException):
            # The deployment was successful, but the return code on one or more
            # steps is bad. Log the exception and do NOT try again!
            raise NonZeroDeploymentException,\
                "One or more Script(s) reported a NonZeroDeployment:%s"\
                % full_deploy_output,\
                sys.exc_info()[2]
        # TODO: Check if all exceptions thrown at this time
        # fall in this category, and possibly don't retry if
        # you hit the Exception block below this.
        _deploy_instance.retry(exc=exc)
    except (BaseException, Exception) as exc:
        celery_logger.exception(exc)
        _deploy_instance.retry(exc=exc)


def _parse_steps_output(msd):
    output = ""
    length = len(msd.steps)
    for idx, script in enumerate(msd.steps):
        output += _parse_script_output(script, idx, length)


def _parse_script_output(script, idx=1, length=1):
    if settings.DEBUG:
        debug_out = "Script:%s" % script.script
    output = "\nBootScript %d/%d: "\
        "%sExitCode:%s Output:%s Error:%s" %\
        (idx + 1, length, debug_out if settings.DEBUG else "",
             script.exit_status, script.stdout, script.stderr)
    return output


@task(name="check_web_desktop_task",
      max_retries=2,
      default_retry_delay=15)
def check_web_desktop_task(driverCls, provider, identity,
                       instance_alias, *args, **kwargs):
    """
    """
    try:
        celery_logger.debug("check_web_desktop_task started at %s." % datetime.now())
        driver = get_driver(driverCls, provider, identity)
        instance = driver.get_instance(instance_alias)
        if not instance:
            return False
        # USE ANSIBLE
        username = identity.user.username
        hostname = build_host_name(instance.id, instance.ip)
        playbooks = run_utility_playbooks(instance.ip, username, instance_alias, ["atmo_check_novnc.yml"], raise_exception=False)
        result = False if execution_has_failures(playbooks, hostname) or execution_has_unreachable(playbooks, hostname)  else True

        # NOTE: Throws Instance.DoesNotExist
        core_instance = Instance.objects.get(provider_alias=instance_alias)
        core_instance.web_desktop = result
        core_instance.save()
        celery_logger.debug("check_web_desktop_task finished at %s." % datetime.now())
        return result
    except AnsibleDeployException as exc:
        check_web_desktop_task.retry(exc=exc)
    except Instance.DoesNotExist:
        celery_logger.warn("check_web_desktop_task failed: Instance %s no longer exists"
                    % instance_alias)
    except (BaseException, Exception) as exc:
        celery_logger.exception(exc)
        check_web_desktop_task.retry(exc=exc)


@task(name="check_process_task",
      max_retries=2,
      default_retry_delay=15)
def check_process_task(driverCls, provider, identity,
                       instance_alias, *args, **kwargs):
    """
    #NOTE: While this looks like a large number (250 ?!) of retries
    # we expect this task to fail often when the image is building
    # and large, uncached images can have a build time.
    # TODO: This should be ansible-ized. Ansible will have already run by the time this process is started.
    """
    try:
        celery_logger.debug("check_process_task started at %s." % datetime.now())
        driver = get_driver(driverCls, provider, identity)
        instance = driver.get_instance(instance_alias)
        if not instance:
            return False
        hostname = build_host_name(instance.id, instance.ip)
        # USE ANSIBLE
        username = identity.user.username
        playbooks = run_utility_playbooks(instance.ip, username, instance_alias, ["atmo_check_vnc.yml"], raise_exception=False)
        result = False if execution_has_failures(playbooks, hostname) or execution_has_unreachable(playbooks, hostname)  else True

        # NOTE: Throws Instance.DoesNotExist
        core_instance = Instance.objects.get(provider_alias=instance_alias)
        core_instance.vnc = result
        core_instance.save()
        celery_logger.debug("check_process_task finished at %s." % datetime.now())
        return result
    except AnsibleDeployException as exc:
        check_process_task.retry(exc=exc)
    except Instance.DoesNotExist:
        celery_logger.warn("check_process_task failed: Instance %s no longer exists"
                    % instance_alias)
    except (BaseException, Exception) as exc:
        celery_logger.exception(exc)
        check_process_task.retry(exc=exc)


@task(name="update_metadata", max_retries=250, default_retry_delay=15)
def update_metadata(driverCls, provider, identity, instance_alias, metadata,
                    replace_metadata=False):
    """
    #NOTE: While this looks like a large number (250 ?!) of retries
    # we expect this task to fail often when the image is building
    # and large, uncached images can have a build time.
    """
    try:
        celery_logger.debug("update_metadata task started at %s." % datetime.now())
        driver = get_driver(driverCls, provider, identity)
        instance = driver.get_instance(instance_alias)
        if not instance:
            return
        return _update_instance_metadata(
            driver, instance, data=metadata, replace=replace_metadata)
        celery_logger.debug("update_metadata task finished at %s." % datetime.now())
    except Exception as exc:
        celery_logger.exception(exc)
        update_metadata.retry(exc=exc)


# Floating IP Tasks
@task(name="add_floating_ip",
      # Defaults will not be used, see countdown call below
      default_retry_delay=15,
      max_retries=30)
def add_floating_ip(driverCls, provider, identity,
                    instance_alias, delete_status=True,
                    *args, **kwargs):
    # For testing ONLY.. Test cases ignore countdown..
    if app.conf.CELERY_ALWAYS_EAGER:
        celery_logger.debug("Eager task waiting 15 seconds")
        time.sleep(15)
    try:
        celery_logger.debug("add_floating_ip task started at %s." % datetime.now())
        # Remove unused floating IPs first, so they can be re-used
        driver = get_driver(driverCls, provider, identity)
        driver._clean_floating_ip()

        # assign if instance doesn't already have an IP addr
        instance = driver.get_instance(instance_alias)
        if not instance:
            celery_logger.debug("Instance has been teminated: %s." % instance_alias)
            return None
        floating_ips = driver._connection.neutron_list_ips(instance)
        if floating_ips:
            floating_ip = floating_ips[0]["floating_ip_address"]
            celery_logger.debug(
                "Reusing existing floating_ip_address - %s" %
                floating_ip)
        else:
            floating_ip = driver._connection.neutron_associate_ip(
                instance, *args, **kwargs)["floating_ip_address"]
            celery_logger.debug("Created new floating_ip_address - %s" % floating_ip)
        _update_status_log(instance, "Networking Complete")
        # TODO: Implement this as its own task, with the result from
        #'floating_ip' passed in. Add it to the deploy_chain before deploy_to
        hostname = build_host_name(instance.id, floating_ip)
        metadata_update = {
            'public-hostname': hostname,
            'public-ip': floating_ip
        }
        # NOTE: This is part of the temp change, should be removed when moving
        # to vxlan
        instance_ports = driver._connection.neutron_list_ports(
            device_id=instance.id)
        network = driver._connection.neutron_get_tenant_network()
        if instance_ports:
            for idx, fixed_ip_port in enumerate(instance_ports):
                fixed_ips = fixed_ip_port.get('fixed_ips', [])
                mac_addr = fixed_ip_port.get('mac_address')
                metadata_update['mac-address%s' % idx] = mac_addr
                metadata_update['port-id%s' % idx] = fixed_ip_port['id']
                metadata_update['network-id%s' % idx] = network['id']
        # EndNOTE:

        update_metadata.s(driverCls, provider, identity, instance.id,
                          metadata_update, replace_metadata=False).apply_async()

        celery_logger.info("Assigned IP:%s - Hostname:%s" % (floating_ip, hostname))
        # End
        celery_logger.debug("add_floating_ip task finished at %s." % datetime.now())
        return {"floating_ip": floating_ip, "hostname": hostname}
    except IpAddressGenerationFailureClient as floating_ip_err:
        if 'no more ip addresses available' in floating_ip_err.message.lower():
            celery_logger.exception("Error occurred while assigning a floating IP")
        countdown = min(2**current.request.retries, 128)
        add_floating_ip.retry(exc=floating_ip_err,
                              countdown=countdown)
    except NeutronBadRequest as bad_request:
        # NOTE: 'Neutron Bad Request' is a good message to 'catch and fix'
        # because its a user-supplied problem.
        # Here we will attempt to 'fix' requests and put the 'add_floating_ip'
        # task back on the queue after we're done.
        celery_logger.exception("Neutron did not accept request - %s."
            % bad_request.message)
        if 'no fixed ip' in bad_request.message.lower():
            fixed_ip = add_fixed_ip(driverCls, provider, identity,
                                    instance_alias)
            if fixed_ip:
                celery_logger.debug("Fixed IP %s has been added to Instance %s."
                             % (fixed_ip, instance_alias))
        # let the exception bubble-up for a retry..
        raise
    except (BaseException, Exception) as exc:
        celery_logger.exception("Error occurred while assigning a floating IP")
        # Networking can take a LONG time when an instance first launches,
        # it can also be one of those things you 'just miss' by a few seconds..
        # So we will retry 30 times using limited exp.backoff
        # Max Time: 53min
        countdown = min(2**current.request.retries, 128)
        add_floating_ip.retry(exc=exc,
                              countdown=countdown)


@task(name="clean_empty_ips", default_retry_delay=15,
      ignore_result=True, max_retries=6)
def clean_empty_ips(driverCls, provider, identity, *args, **kwargs):
    try:
        celery_logger.debug("remove_floating_ip task started at %s." %
                     datetime.now())
        driver = get_driver(driverCls, provider, identity)
        ips_cleaned = driver._clean_floating_ip()
        celery_logger.debug("remove_floating_ip task finished at %s." %
                     datetime.now())
        return ips_cleaned
    except Exception as exc:
        celery_logger.warn(exc)
        clean_empty_ips.retry(exc=exc)


# project Network Tasks
@task(name="add_os_project_network",
      default_retry_delay=15,
      ignore_result=True,
      max_retries=6)
def add_os_project_network(core_identity, *args, **kwargs):
    try:
        celery_logger.debug("add_os_project_network task started at %s." %
                     datetime.now())
        account_driver = get_account_driver(core_identity.provider)
        account_driver.create_network(core_identity)
        celery_logger.debug("add_os_project_network task finished at %s." %
                     datetime.now())
    except Exception as exc:
        add_os_project_network.retry(exc=exc)


@task(name="remove_empty_network",
      default_retry_delay=60,
      max_retries=1)
def remove_empty_network(
        driverCls, provider, identity,
        core_identity_uuid,
        network_options):
    try:
        # For testing ONLY.. Test cases ignore countdown..
        if app.conf.CELERY_ALWAYS_EAGER:
            celery_logger.debug("Eager task waiting 1 minute")
            time.sleep(60)
        celery_logger.debug("remove_empty_network task started at %s." %
                     datetime.now())

        celery_logger.debug("CoreIdentity(uuid=%s)" % core_identity_uuid)
        core_identity = Identity.objects.get(uuid=core_identity_uuid)
        driver = get_driver(driverCls, provider, identity)
        instances = driver.list_instances()
        active_instances = any(
            driver._is_active_instance(instance) for
            instance in instances)
        # If instances are active, we are done..
        if not active_instances:
            # Inactive True IFF ALL instances are suspended/stopped, False if empty list.
            inactive_instances_present = all(
                driver._is_inactive_instance(instance)
                for instance in instances)
            # Inactive instances, True: Remove network, False
            # Check for project network
            celery_logger.info(
                "No active instances. Removing project network"
                "from %s" % core_identity)
            delete_network_options = {}
            delete_network_options['skip_network'] = inactive_instances_present
            os_acct_driver = get_account_driver(core_identity.provider)
            os_acct_driver.delete_user_network(
                core_identity, delete_network_options)
            if not inactive_instances_present:
                # Sec. group can't be deleted if instances are suspended
                # when instances are suspended we should leave this intact.
                os_acct_driver.delete_security_group(core_identity)
            return True
        celery_logger.debug("remove_empty_network task finished at %s." %
                     datetime.now())
        return False
    except Exception as exc:
        celery_logger.exception("Exception occurred project network is empty")


@task(name="check_image_membership")
def check_image_membership():
    try:
        celery_logger.debug("check_image_membership task started at %s." %
                     datetime.now())
        update_membership()
        celery_logger.debug("check_image_membership task finished at %s." %
                     datetime.now())
    except Exception as exc:
        celery_logger.exception('Error during check_image_membership task')
        check_image_membership.retry(exc=exc)


@task(name="update_membership_for")
def update_membership_for(provider_uuid):
    from core.models import Provider, ProviderMachine
    provider = Provider.objects.get(uuid=provider_uuid)
    if not provider.is_active():
        return
    if provider.type.name.lower() == 'openstack':
        acct_driver = get_account_driver(provider)
    else:
        celery_logger.warn("Encountered unknown ProviderType:%s, expected"
                    " [Openstack] " % (provider.type.name,))
        return
    if not acct_driver:
        raise Exception("Encountered error creating driver -- check 'get_account_driver'")
    images = acct_driver.list_all_images()
    changes = 0
    for img in images:
        pm = ProviderMachine.objects.filter(instance_source__identifier=img.id,
                                            instance_source__provider=provider)
        if not pm or len(pm) > 1:
            celery_logger.debug("pm filter is bad!")
            celery_logger.debug(pm)
            return
        else:
            pm = pm[0]
        app_manager = pm.application_version.application.applicationmembership_set
        if img.get('visibility','') is not 'public':
            # Lookup members
            image_members = acct_driver.image_manager.shared_images_for(
                image_id=img.id)
            # add machine to each member
            #(Who owns the cred:ex_project_name) in MachineMembership
            # for member in image_members:
        else:
            members = app_manager.all()
            # if MachineMembership exists, remove it (No longer private)
            if members:
                celery_logger.info("Application for PM:%s used to be private."
                            " %s Users membership has been revoked. "
                            % (img.id, len(members)))
                changes += len(members)
                members.delete()
    celery_logger.info("Total Updates to machine membership:%s" % changes)


@task(name="update_membership")
def update_membership():
    from core.models.provider import Provider as CoreProvider
    for provider in CoreProvider.objects.all():
        update_membership_for.apply_async(args=[provider.uuid])


def test_active_instances(instances):
    tested_instances = {}
    for instance in instances:
        results = test_instance_links(instance.alias, instance.ip)
        tested_instances.update(results)
    return tested_instances


def test_instance_links(alias, uri):
    from rtwo.linktest import test_link
    vnc_address = 'http://%s:5904' % uri
    try:
        vnc_success = test_link(vnc_address)
    except Exception as e:
        celery_logger.exception("Bad vnc address: %s" % vnc_address)
        vnc_success = False
    return {alias: {'vnc': vnc_success}}


def update_links(instances):
    updated = []
    linktest_results = test_active_instances(instances)
    for (instance_id, link_results) in linktest_results.items():
        try:
            update = False
            instance = Instance.objects.get(provider_alias=instance_id)
            if link_results['vnc'] != instance.vnc:
                celery_logger.debug('Change Instance %s VNC %s-->%s' %
                             (instance, instance.vnc,
                              link_results['vnc']))
                instance.vnc = link_results['vnc']
                update = True
            if update:
                instance.save()
                updated.append(instance)
        except Instance.DoesNotExist:
            continue
    celery_logger.debug("Instances updated: %d" % len(updated))
    return updated


def _cleanup_traceback(err_str):
    """
    Given a Traceback message, return the 'human readable' response.
    If unknown, return the full traceback to help staff trace down the error quickly.
    """
    if 'AnsibleDeployException' in err_str and 'inject_ssh_keys' in err_str:
        err_str = "One or more SSH Keys could not be deployed to the instance. Please verify the public-key is correct."
    elif 'NonZeroDeploymentException' in err_str:
        err_str = err_str.partition("NonZeroDeploymentException:")[2].strip()
    return err_str
