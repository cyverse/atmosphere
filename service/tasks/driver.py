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

from rtwo.exceptions import LibcloudInvalidCredsError, LibcloudBadResponseError

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
    instance_deploy, user_deploy,
    build_host_name,
    ready_to_deploy as ansible_ready_to_deploy,
    run_utility_playbooks, execution_has_failures, execution_has_unreachable
    )
from service.driver import get_driver, get_account_driver
from service.exceptions import AnsibleDeployException
from service.instance import _update_instance_metadata
from service.networking import _generate_ssh_kwargs

from service.mock import MockInstance

def _update_status_log(instance, status_update):
    if type(instance) == MockInstance:
        return
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
            celery_logger.debug("Instance has been teminated: %s." % instance_alias)
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
        test_tmp_status=False,
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
        driver = get_driver(driverCls, provider, identity)
        instance = driver.get_instance(instance_alias)
        if not instance:
            celery_logger.debug("Instance has been terminated: %s." % instance_alias)
            return False
        result = _is_instance_ready(instance, status_query,
                                    tasks_allowed, test_tmp_status, return_id)
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


def _is_instance_ready(instance, status_query,
                       tasks_allowed=False, test_tmp_status=False, return_id=False):
    # TODO: Refactor so that terminal states can be found. IE if waiting for
    # 'active' and in status: Suspended - none - GIVE up!!
    i_status = instance._node.extra['status'].lower()
    i_task = instance._node.extra.get('task',None)
    i_tmp_status = instance._node.extra.get('metadata', {}).get('tmp_status', '')
    celery_logger.debug(
        "Instance %s: Status: (%s - %s) Tmp status: %s "
        % (instance.id, i_status, i_task, i_tmp_status))
    status_not_ready = (i_status not in status_query)  # Ex: status 'build' is not in 'active'
    tasks_not_ready = (not tasks_allowed and i_task is not None)  # Ex: Task name: 'scheudling', tasks_allowed=False
    tmp_status_not_ready = (test_tmp_status and i_tmp_status != "")  # Ex: tmp_status: 'initializing'
    celery_logger.debug(
            "Status not ready: %s tasks not ready: %s Tmp status_not_ready: %s"
            % (status_not_ready, tasks_not_ready, tmp_status_not_ready))
    if status_not_ready or tasks_not_ready or tmp_status_not_ready:
        raise Exception(
            "Instance: %s: Status: (%s - %s - %s) Produced:"
            "Status not ready: %s tasks not ready: %s Tmp status_not_ready: %s"
            % (instance.id, i_status, i_task, i_tmp_status,
               status_not_ready, tasks_not_ready, tmp_status_not_ready))
    celery_logger.debug(
            "Instance %s: Status: (%s - %s - %s) - Ready"
            % (instance.id, i_status, i_task, i_tmp_status))
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
    from service.instance import _to_network_driver, _get_network_id
    try:
        celery_logger.debug("add_fixed_ip task started at %s." % datetime.now())
        core_identity = Identity.objects.get(uuid=core_identity_uuid)
        network_driver = _to_network_driver(core_identity)
        driver = get_driver(driverCls, provider, identity)
        instance = driver.get_instance(instance_id)
        if not instance:
            celery_logger.debug("Instance has been teminated: %s." % instance_id)
            return None

        ports = network_driver.list_ports(device_id=instance.id)
        # Catch a common scenario that breaks networking
        assert len(ports) == 1, "Attaching a fixed ip requires a single port"
        port = ports[0]
        port_zone = instance_zone = None
        try:
            port_zone = port['device_owner'].split(":")[1]
            instance_zone = instance.extra['availability_zone']
        except:
            pass

        network_id = _get_network_id(driver, instance)

        if port_zone and instance_zone and port_zone != instance_zone:
            # If the port and instance are in different zones, delete the old
            # port and attach a new one, this only occurs in narrow scenarios
            # documented in the following ticket:
            # https://bugs.launchpad.net/nova/+bug/1759924
            network_driver.delete_port(port)
            driver._connection.ex_attach_interface(
                instance.id, network_id=network_id)

        elif not instance._node.private_ips:
            # Only add fixed ip if the instance doesn't already have one
            driver._connection.ex_add_fixed_ip(instance, network_id)

        celery_logger.debug("add_fixed_ip task finished at %s." % datetime.now())
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


def _remove_ips_from_inactive_instances(driver, instances, core_identity):
    from service import instance as instance_service
    for instance in instances:
        # DOUBLE-CHECK:
        if driver._is_inactive_instance(instance) and instance.ip:
            # If an inactive instance has floating IP.. Remove it!
            instance_service.remove_floating_ip(driver, instance, str(core_identity.uuid))
    return True


@task(name="clear_empty_ips_for")
def clear_empty_ips_for(username, core_provider_id, core_identity_uuid):
    """
    RETURN: number_ips_removed
    on Failure:
    -404, driver creation failure (Verify credentials are accurate)
    -401, authorization failure (Change the password of the driver)
    -500, cloud failure (Operational support required)
    """
    from service.driver import get_esh_driver
    from rtwo.driver import OSDriver
    # Initialize the drivers
    core_identity = Identity.objects.get(uuid=core_identity_uuid)
    driver = get_esh_driver(core_identity)
    if not isinstance(driver, OSDriver):
        return -404
    # Get useful info
    creds = core_identity.get_credentials()
    tenant_name = creds['ex_tenant_name']
    celery_logger.info("Checking Identity %s" % tenant_name)
    # Attempt to clean floating IPs
    num_ips_removed = _remove_extra_floating_ips(driver, tenant_name)
    # Test for active/inactive_instances instances
    try:
        instances = driver.list_instances()
    except LibcloudInvalidCredsError:
        logger.exception("InvalidCredentials provided for Identity %s" % core_identity)
        return -401
    except LibcloudBadResponseError:
        logger.exception("Driver returned unexpected response for Identity %s" % core_identity)
        return -500
    _remove_ips_from_inactive_instances(driver, instances, core_identity)


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
            clear_empty_ips_for.apply_async(args=[core_identity.created_by.username,core_identity.provider.id, str(core_identity.uuid)])
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
        context,
        exception_msg,
        traceback,
        driverCls,
        provider,
        identity,
        instance_id,
        user,
        message=None,
        **celery_task_args):
    try:
        celery_logger.debug("user_deploy_failed task started at %s." % datetime.now())
        celery_logger.info("failed task context=%s" % (context,))
        celery_logger.info("exception_msg=%s" % (exception_msg,))
        err_str = "Error Traceback:%s" % (traceback,)
        celery_logger.error(err_str)
        # Send deploy email
        _send_instance_email_with_failure(driverCls, provider, identity, instance_id, user.username, err_str)
        # Update metadata on the instance -- use the last 255 chars of traceback (Metadata limited)
        limited_trace = str(traceback)[-255:]
        metadata = {
            'tmp_status': 'user_deploy_error',
            'fault_message': str(exception_msg),
            'fault_trace': limited_trace
        }
        update_metadata.s(driverCls, provider, identity, instance_id,
                          metadata, replace_metadata=False).apply_async()
        celery_logger.debug("user_deploy_failed task finished at %s." % datetime.now())
        return err_str
    except Exception as exc:
        celery_logger.warn(exc)
        user_deploy_failed.retry(exc=exc)


@task(name="deploy_failed")
def deploy_failed(
        context,
        exception_msg,
        traceback,
        driverCls,
        provider,
        identity,
        instance_id,
        **celery_task_args):
    try:
        celery_logger.debug("deploy_failed task started at %s." % datetime.now())
        celery_logger.info("failed task context=%s" % (context,))
        celery_logger.info("exception_msg=%s" % (exception_msg,))
        err_str = "DEPLOYERROR::%s" % (traceback,)
        celery_logger.error(err_str)
        driver = get_driver(driverCls, provider, identity)
        instance = driver.get_instance(instance_id)
        limited_trace = str(traceback)[-255:]
        metadata = {
            'tmp_status': 'deploy_error',
            'fault_message': str(exception_msg),
            'fault_trace': limited_trace}
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
    elif tmp_status in ['', 'redeploying', 'deploying', 'deploy_error', 'user_deploy_error']:
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
            "Instance has a tmp_status that is NOT: [initializing, networking, deploying, redeploying] - %s" %
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
    has_secret = core_identity.get_credential('secret') is not None
    if not has_secret:
        add_security_group = add_security_group_task.si(driverCls, provider, core_identity, instance.id)
        wait_active_task.link(add_security_group)
    start_chain = wait_active_task
    network_start = get_chain_from_active_no_ip(
        driverCls, provider, identity, instance, core_identity, username=username,
        password=password, redeploy=redeploy, deploy=deploy)
    if not has_secret:
        add_security_group.link(network_start)
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
    for next in next_tasks:
        mystr += print_chain(next, idx+1)
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
    networking_task = add_floating_ip.si(
        driverCls, provider, identity, str(core_identity.uuid), instance.id, delete_status=False)
    networking_task.link_error(
        deploy_failed.s(driverCls, provider, identity, instance.id))

    if instance.extra.get('metadata', {}).get('tmp_status', '') == 'networking':
        start_chain = networking_task
    else:
        start_chain = network_meta_task
        start_chain.link(networking_task)
    end_chain = networking_task
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
        driverCls, provider, identity, instance.id, str(core_identity.uuid))
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
        {
            'tmp_status': 'deploying',
            'fault_message': "",
            'fault_trace': ""
        })

    deploy_task = _deploy_instance.si(
        driverCls, provider, identity, instance.id,
        username, None, redeploy)
    deploy_user_task = _deploy_instance_for_user.si(
        driverCls, provider, identity, instance.id,
        username, redeploy)
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


    # (SUCCESS_)LINKS and ERROR_LINKS
    deploy_task.link_error(
        deploy_failed.s(driverCls, provider, identity, instance.id))
    deploy_user_task.link_error(user_deploy_failed_task)
    # Note created new 'copy' of remove_status to avoid potential for email*2
    user_deploy_failed_task.link(remove_status_on_failure_task)

    deploy_ready_task.link(deploy_meta_task)
    deploy_ready_task.link_error(
        deploy_failed.s(driverCls, provider, identity, instance.id))
    deploy_meta_task.link(deploy_task)
    deploy_task.link(check_web_desktop)
    check_web_desktop.link(check_vnc_task)  # Above this line, atmo is responsible for success.

    check_web_desktop.link_error(
        deploy_failed.s(driverCls, provider, identity, instance.id))
    check_vnc_task.link(deploy_user_task)  # this line and below, user can create a failure.
    # ready -> metadata -> deployment..

    deploy_user_task.link(remove_status_chain)
    # Final task at this point should be 'remove_status_chain'

    # Only send emails when 'redeploy=False'
    if not redeploy:
        remove_status_chain.link(email_task)
    celery_logger.info("Deploy Chain : %s" % print_chain(start_chain, idx=0))
    return start_chain


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
        failure_task = deploy_failed.si(
            {},
            "Test Error Message",
            "Longer Error Traceback\nMultiline\noutput.",
            driver.__class__,
            driver.provider,
            driver.identity,
            instance_id,
        )
        failure_task.apply_async()


@task(name="deploy_ready_test",
      default_retry_delay=64,
      soft_time_limit=120,
      max_retries=115  # Attempt up to two hours
      )
def deploy_ready_test(driverCls, provider, identity, instance_id, core_identity_uuid,
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
        # TODO: Improvement -- keep 'count' of # times instance doesn't appear.
        # After n consecutive attempts, force a 'bail-out'
        # rather than wait for all retries to complete.
        if not instance:
            celery_logger.debug("Instance has been teminated: %s." % instance_id)
            raise Exception("Instance maybe terminated? "
                            "-- Going to keep trying anyway")
        if not instance.ip:
            celery_logger.debug("Instance IP address missing from : %s." % instance_id)
            raise Exception("Instance IP Missing? %s" % instance_id)

        # HACK: A race-condition exists where an instance may enter this task with _two_ private IPs
        # If this happens, it is _possible_ that the Fixed IP port is invalid.
        # The method below will attempt to correct that behavior _prior_ to seeing if the instance
        # networking is indeed ready.
        if len(instance._node.private_ips) >= 2:
            _update_floating_ip_to_active_fixed_ip(driver, instance, core_identity_uuid)
    except (BaseException, Exception) as exc:
        celery_logger.exception(exc)
        _deploy_ready_failed_email_test(
            driver, instance_id, exc.message, current.request, deploy_ready_test)
        deploy_ready_test.retry(exc=exc)
    # USE ANSIBLE
    try:
        username = identity.user.username
        playbook_results = ansible_ready_to_deploy(instance.ip, username, instance_id)
        _update_status_log(instance, "Ansible Finished (ready test) for %s." % instance.ip)
        celery_logger.debug("deploy_ready_test task finished at %s." % datetime.now())
    except AnsibleDeployException as exc:
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
                    username=None, redeploy=False,
                    **celery_task_args):
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

    except (BaseException, Exception) as exc:
        celery_logger.exception(exc)
        _deploy_instance.retry(exc=exc)
    try:
        username = identity.user.username
        # FIXME: first_deploy would be more reliable if it was based
        # on InstanceStatusHistory (made it to 'active'), otherwise,
        # an instance that 'networking'->'deploy_error'->'redeploy'
        # would miss out on scripts that require first_deploy == True..
        # This will work for initial testing.
        first_deploy = not redeploy
        user_deploy(instance.ip, username, instance_id, first_deploy=first_deploy)
        _update_status_log(instance, "Ansible Finished for %s." % instance.ip)
        celery_logger.debug("_deploy_instance_for_user task finished at %s." % datetime.now())
    except AnsibleDeployException as exc:
        celery_logger.exception(exc)
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
    except (BaseException, Exception) as exc:
        celery_logger.exception(exc)
        _deploy_instance.retry(exc=exc)


@task(name="check_web_desktop_task", max_retries=4, default_retry_delay=15)
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
        should_raise = True
        retry_count = current.request.retries
        if retry_count > 2:
            should_raise = False
        playbook_results = run_utility_playbooks(instance.ip, username, instance_alias, ["atmo_check_novnc.yml"], raise_exception=should_raise)
        desktop_enabled = not (execution_has_failures(playbook_results) or execution_has_unreachable(playbook_results))

        # NOTE: Throws Instance.DoesNotExist
        core_instance = Instance.objects.get(provider_alias=instance_alias)
        core_instance.web_desktop = desktop_enabled
        core_instance.save()
        celery_logger.debug("check_web_desktop_task finished at %s." % datetime.now())
        return desktop_enabled
    except AnsibleDeployException as exc:
        check_web_desktop_task.retry(exc=exc)
    except Instance.DoesNotExist:
        celery_logger.warn("check_web_desktop_task failed: Instance %s no longer exists"
                    % instance_alias)
    except (BaseException, Exception) as exc:
        celery_logger.exception(exc)
        check_web_desktop_task.retry(exc=exc)


@task(name="add_security_group_task",
      max_retries = 5,
      default_retry_delay=10)
def add_security_group_task(driverCls, provider, core_identity,
                            instance_alias, *args, **kwargs):
    """
    Assign the security group to the instance using the OpenStack Nova API
    """
    from service.instance import _to_user_driver
    user_driver = _to_user_driver(core_identity)
    user_nova = user_driver.nova
    try:
        server_instance = user_nova.servers.get(instance_alias)
    except:
        raise Exception("Cannot find the instance")
    try:
        security_group_name = core_identity.provider.get_config("network", "security_group_name", "default")
        server_instance.add_security_group(security_group_name)
    except:
        raise Exception("Cannot add the security group to the instance usng nova")
    return True



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
        # USE ANSIBLE
        username = identity.user.username
        playbook_results = run_utility_playbooks(instance.ip, username, instance_alias, ["atmo_check_vnc.yml"], raise_exception=False)
        vnc_enabled = not (execution_has_failures(playbook_results) or execution_has_unreachable(playbook_results))

        # NOTE: Throws Instance.DoesNotExist
        core_instance = Instance.objects.get(provider_alias=instance_alias)
        core_instance.vnc = vnc_enabled
        core_instance.save()
        celery_logger.debug("check_process_task finished at %s." % datetime.now())
        return vnc_enabled
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
def add_floating_ip(driverCls, provider, identity, core_identity_uuid,
                    instance_alias, delete_status=True,
                    *args, **kwargs):
    # For testing ONLY.. Test cases ignore countdown..
    from service import instance as instance_service
    if app.conf.CELERY_ALWAYS_EAGER:
        celery_logger.debug("Eager task waiting 15 seconds")
        time.sleep(15)
    try:
        celery_logger.debug("add_floating_ip task started at %s." % datetime.now())
        core_identity = Identity.objects.get(uuid=core_identity_uuid)

        # NOTE: This if statement is a HACK! It will be removed when IP management is enabled in an upcoming version. -SG
        if core_identity.provider.location != 'iPlant Cloud - Tucson':
            # Remove unused floating IPs first, so they can be re-used
            driver = get_driver(driverCls, provider, identity)
            driver._clean_floating_ip()
        # ENDNOTE
        driver = get_driver(driverCls, provider, identity)

        instance = driver.get_instance(instance_alias)
        if not instance:
            celery_logger.debug("Instance has been teminated: %s." % instance_alias)
            return None
        network_driver = instance_service._to_network_driver(core_identity)

        floating_ips = network_driver.list_floating_ips()
        floating_ip_addr = None
        selected_floating_ip = None
        if floating_ips:
            instance_floating_ips = [fip for fip in floating_ips if fip.get("instance_id",'') == instance_alias]
            selected_floating_ip = instance_floating_ips[0] if instance_floating_ips else None

        if selected_floating_ip:
            floating_ip_addr = selected_floating_ip["floating_ip_address"]
            celery_logger.debug(
                "Skip floating IP add:"
                " address %s already exists for Instance %s",
                floating_ip_addr, instance_alias)
            floating_ip = selected_floating_ip
        else:
            if core_identity.provider.cloud_config['network']['topology'] \
                    == "External Router Topology":
                # Determine correct external network based on external gateway
                # info of the identity's public router
                public_router_name = core_identity.get_credential('router_name')
                admin_identity = core_identity.provider.admin
                admin_neutron = instance_service._to_network_driver(admin_identity).neutron
                routers = admin_neutron.list_routers(retrieve_all=True)['routers']
                public_router = None
                for router in routers:
                    if router['name'] == public_router_name:
                        public_router = router
                if not public_router:
                    raise Exception("Could not find a router matching"
                                    " public_router name {} for user {}"
                                    .format(public_router_name,
                                            identity.created_by.username))
                external_network_id = \
                    public_router['external_gateway_info']['network_id']
                floating_ip = \
                    network_driver.associate_floating_ip(instance_alias,
                                                         external_network_id)
            else:
                floating_ip = \
                    network_driver.associate_floating_ip(instance_alias)
            floating_ip_addr = \
                floating_ip["floating_ip_address"]
            celery_logger.debug("Created new floating_ip_address - %s" % floating_ip_addr)

        _update_status_log(instance, "Networking Complete")
        # TODO: Implement this as its own task, with the result from
        #'floating_ip' passed in. Add it to the deploy_chain before deploy_to
        hostname = build_host_name(instance.id, floating_ip_addr)
        metadata_update = {
            'public-hostname': hostname,
            'public-ip': floating_ip_addr
        }
        # NOTE: This is part of the temp change, should be removed when moving
        # to vxlan
        instance_ports = network_driver.list_ports(
            device_id=instance.id)
        network = network_driver.tenant_networks()
        if type(network) is list:
            network = [net for net in network if net['subnets'] != []][0]
        if instance_ports:
            for idx, fixed_ip_port in enumerate(instance_ports):
                # fixed_ips = fixed_ip_port.get('fixed_ips', [])
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
    except NeutronBadRequest:
        # This is an error on our end, we want it to surface
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


def _update_floating_ip_to_active_fixed_ip(driver, instance, core_identity_uuid):
    """
    - Given an instance matching the input described:
      - determine which fixed IP is 'active' and valid for connection
      - If floating IP is not set to that fixed IP, update the floating IP accordingly

    Input: An instance with 2+ private/fixed IPs and 1+ floating IP attached
    Output: Floating IP associated with an ACTIVE 'fixed IP' port, attached to instance.
    Notes:
      - In a future where >1 fixed IP and >1 floating IP is "normal"
        this method will need to be changed/removed.
    """
    # Determine which port is the active port
    from service import instance as instance_service
    core_identity = Identity.objects.get(uuid=core_identity_uuid)
    network_driver = instance_service._to_network_driver(core_identity)
    port_id = _select_port_id(network_driver, driver, instance)
    instance_id = instance.id
    # NOTE: Strategy is to manage only the first floating IP address. Other IP addresses would be managed by user.
    floating_ip_addr = selected_floating_ip = None
    floating_ips = network_driver.list_floating_ips()
    instance_floating_ips = [fip for fip in floating_ips if fip.get("instance_id", '') == instance_id]
    selected_floating_ip = instance_floating_ips[0] if instance_floating_ips else None
    if selected_floating_ip and port_id:
        floating_ip_addr = selected_floating_ip["floating_ip_address"]
        previous_port_id = selected_floating_ip["port_id"]
        if previous_port_id != port_id:
            celery_logger.info(
                "Re-setting existing floating_ip_address %s port: %s -> %s",
                floating_ip_addr, previous_port_id, port_id)
            selected_floating_ip = network_driver.neutron.update_floatingip(selected_floating_ip['id'], {'floatingip': {'port_id': port_id}})
    return selected_floating_ip


def _select_port_id(network_driver, driver, instance):
    """
    - Input: Instance with two fixed IPs (will fail networking)
      Output: Instance with one, valid fixed IP
    """
    instance_alias = instance.id
    fixed_ip_ports = [p for p in network_driver.list_ports() if p['device_id'] == instance_alias]
    active_fixed_ip_ports = [p for p in fixed_ip_ports if 'ACTIVE' in p['status']]
    # Select the first active fixed ip port.
    # nt.
    if not active_fixed_ip_ports:
        logger.warn(
            "Instance %s has >1 Fixed IPs AND neither is ACTIVE."
            " Ports found: %s", instance_alias, fixed_ip_ports)
    port_id = active_fixed_ip_ports[0]['id']
    return port_id


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
