"""
Tasks for driver operations.
"""
from operator import attrgetter
import re
import time

from django.conf import settings
from django.utils.timezone import datetime
from celery import chain
from celery.contrib import rdb
from celery.decorators import task
from celery.task import current
from celery.result import allow_join_result
from celery.task.schedules import crontab

from libcloud.compute.types import Provider, NodeState, DeploymentError

from rtwo.exceptions import NonZeroDeploymentException

from threepio import logger, status_logger

from atmosphere.celery import app
from atmosphere.settings.local import ATMOSPHERE_PRIVATE_KEYFILE

from core.email import send_instance_email
from core.ldap import get_uid_number as get_unique_number
from core.models.identity import Identity
from core.models.profile import UserProfile

from service.deploy import init, check_process
from service.driver import get_driver, get_esh_driver, get_account_driver
from service.instance import update_instance_metadata
from service.instance import _create_and_attach_port
from service.networking import _generate_ssh_kwargs


def _update_status_log(instance, status_update):
    now_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        user = instance._node.extra['metadata']['creator']
    except KeyError, no_user:
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
    logger.debug(log_str)


@task(name="complete_resize", max_retries=2, default_retry_delay=15)
def complete_resize(driverCls, provider, identity, instance_alias,
                    core_provider_id, core_identity_id, user):
    """
    Confirm the resize of 'instance_alias'
    """
    from service import instance as instance_service
    try:
        logger.debug("complete_resize task started at %s." % datetime.now())
        driver = get_driver(driverCls, provider, identity)
        instance = driver.get_instance(instance_alias)
        if not instance:
            logger.debug("Instance has been teminated: %s." % instance_id)
            return False, None
        result = instance_service.confirm_resize(
            driver, instance, core_provider_id, core_identity_id, user)
        logger.debug("complete_resize task finished at %s." % datetime.now())
        return True, result
    except Exception as exc:
        logger.exception(exc)
        complete_resize.retry(exc=exc)



@task(name="wait_for_instance", max_retries=250, default_retry_delay=15)
def wait_for_instance(instance_alias, driverCls, provider, identity, status_query,
             tasks_allowed=False, return_id=False, **task_kwargs):
    """
    #Task makes 250 attempts to 'look at' the instance, waiting 15sec each try
    Cumulative time == 1 hour 2 minutes 30 seconds before FAILURE

    status_query = "active" Match only one value, active
    status_query = ["active","suspended"] or match multiple values.
    """
    from service import instance as instance_service
    try:
        logger.debug("wait_for task started at %s." % datetime.now())
        if app.conf.CELERY_ALWAYS_EAGER:
            logger.debug("Eager task - DO NOT return until its ready!")
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
            logger.exception(exc)
        wait_for_instance.retry(exc=exc)


def _eager_override(task_class, run_method, args, kwargs):
    attempts = 0
    delay = task_class.default_retry_delay or 30  # Seconds
    while attempts < task_class.max_retries:
        try:
            result = run_method(*args, **kwargs)
            return result
        except Exception as exc:
            logger.exception("Encountered error while running eager")
        attempts += 1
        logger.info("Waiting %d seconds" % delay)
        time.sleep(delay)
    return None


def _is_instance_ready(driverCls, provider, identity,
                       instance_alias, status_query,
                       tasks_allowed=False, return_id=False):
    driver = get_driver(driverCls, provider, identity)
    instance = driver.get_instance(instance_alias)
    if not instance:
        logger.debug("Instance has been terminated: %s." % instance.id)
        if return_id:
            return None
        return False
    i_status = instance._node.extra['status'].lower()
    i_task = instance._node.extra['task']
    if (i_status not in status_query) or (i_task and not tasks_allowed):
        raise Exception(
            "Instance: %s: Status: (%s - %s) - Not Ready"
            % (instance.id, i_status, i_task))
    logger.debug("Instance %s: Status: (%s - %s) - Ready"
                 % (instance.id, i_status, i_task))
    if return_id:
        return instance.id
    return True


@task(name="add_fixed_ip",
      ignore_result=True,
      default_retry_delay=15,
      max_retries=15)
def add_fixed_ip(driverCls, provider, identity, instance_id, core_identity_id=None):
    from service import instance as instance_service
    try:
        logger.debug("add_fixed_ip task started at %s." % datetime.now())
        driver = get_driver(driverCls, provider, identity)
        instance = driver.get_instance(instance_id)
        if not instance:
            logger.debug("Instance has been teminated: %s." % instance_id)
            return None
        if instance._node.private_ips:
            #TODO: Attempt to rescue
            logger.info("Instance has fixed IP: %s" % instance_id)
            return instance

        network_id = instance_service._get_network_id(driver, instance)
        fixed_ip = driver._connection.ex_add_fixed_ip(instance, network_id)
        logger.debug("add_fixed_ip task finished at %s." % datetime.now())
        return fixed_ip
    except Exception as exc:
        if "Not Ready" not in str(exc):
            # Ignore 'normal' errors.
            logger.exception(exc)
        add_fixed_ip.retry(exc=exc)

@task(name="clear_empty_ips")
def clear_empty_ips():
    logger.debug("clear_empty_ips task started at %s." % datetime.now())
    from service import instance as instance_service
    from rtwo.driver import OSDriver
    from service.accounts.openstack import AccountDriver as\
        OSAccountDriver

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
        logger.debug("Removed %s ips from OpenStack Tenant %s"
                     % (num_ips_removed, tenant_name))
    return num_ips_removed

def _remove_ips_from_inactive_instances(driver, instances):
    from service import instance as instance_service
    for instance in instances:
        #DOUBLE-CHECK:
        if driver._is_inactive_instance(instance) and instance.ip:
            # If an inactive instance has floating/fixed IPs.. Remove them!
            instance_service.remove_ips(driver, instance)
    return True

def _remove_network(os_acct_driver, core_identity, tenant_name, remove_network=False):
    """
    """
    if not remove_network:
        return
    logger.info("Removing project network for %s" % tenant_name)
    #Sec. group can't be deleted if instances are suspended
    # when instances are suspended we pass remove_network=False
    os_acct_driver.delete_security_group(core_identity)
    os_acct_driver.delete_network(
        core_identity,
        remove_network=remove_network)
    return True


@task(name="clear_empty_ips_for", queue="celery_periodic")
def clear_empty_ips_for(core_identity_id, username=None):
    """
    RETURN: (number_ips_removed, delete_network_called)
    """
    from api import get_esh_driver
    from rtwo.driver import OSDriver
    #Initialize the drivers
    core_identity = Identity.objects.get(id=core_identity_id)
    driver = get_esh_driver(core_identity)
    if not isinstance(driver, OSDriver):
        return (0, False)
    os_acct_driver = get_account_driver(core_identity.provider)
    logger.info("Initialized account driver")
    # Get useful info
    creds = core_identity.get_credentials()
    tenant_name = creds['ex_tenant_name']
    logger.info("Checking Identity %s" % tenant_name)
    # Attempt to clean floating IPs
    num_ips_removed = _remove_extra_floating_ips(driver, tenant_name)
    #Test for active/inactive instances
    instances = driver.list_instances()
    #Active IFF ANY instance is 'active'
    active = any(driver._is_active_instance(inst)
                 for inst in instances)
    #Inactive IFF ALL instances are suspended/stopped
    inactive = all(driver._is_inactive_instance(inst)
                   for inst in instances)
    _remove_ips_from_inactive_instances(driver, instances)
    if active and not inactive:
        #User has >1 active instances AND not all instances inactive
        return (num_ips_removed, False)
    network_id = os_acct_driver.network_manager.get_network_id(
            os_acct_driver.network_manager.neutron,
            '%s-net' % tenant_name)
    if network_id:
        #User has 0 active instances OR all instances are inactive
        #Network exists, attempt to dismantle as much as possible
        # Remove network=False IFF inactive=True..
        remove_network = not inactive
        if remove_network:
            _remove_network(os_acct_driver, core_identity, tenant_name, remove_network=True)
            return (num_ips_removed, True)
        return (num_ips_removed, False)
    else:
        logger.info("No Network found. Skipping %s" % tenant_name)
        return (num_ips_removed, False)

@task(name="clear_empty_ips")
def clear_empty_ips():
    logger.debug("clear_empty_ips task started at %s." % datetime.now())
    identities = current_openstack_identities()
    for core_identity in identities:
        try:
            #TODO: Add some 
            clear_empty_ips_for.apply_async(args=[core_identity.id,
                                      core_identity.created_by])
        except Exception as exc:
            logger.exception(exc)
    logger.debug("clear_empty_ips task finished at %s." % datetime.now())


@task(name="_send_instance_email",
      default_retry_delay=10,
      max_retries=2)
def _send_instance_email(driverCls, provider, identity, instance_id):
    try:
        logger.debug("_send_instance_email task started at %s." %
                     datetime.now())
        driver = get_driver(driverCls, provider, identity)
        instance = driver.get_instance(instance_id)
        #Breakout if instance has been deleted at this point
        if not instance:
            logger.debug("Instance has been teminated: %s." % instance_id)
            return
        username = identity.user.username
        profile = UserProfile.objects.get(user__username=username)
        if profile.send_emails:
            #Only send emails if allowed by profile setting
            created = datetime.strptime(instance.extra['created'],
                                        "%Y-%m-%dT%H:%M:%SZ")
            send_instance_email(username,
                                instance.id,
                                instance.name,
                                instance.ip,
                                created,
                                username)
        else:
            logger.debug("User %s elected NOT to receive new instance emails"
                         % username)

        logger.debug("_send_instance_email task finished at %s." %
                     datetime.now())
    except Exception as exc:
        logger.warn(exc)
        _send_instance_email.retry(exc=exc)


# Deploy and Destroy tasks
@task(name="deploy_failed")
def deploy_failed(task_uuid, driverCls, provider, identity, instance_id,
                  **celery_task_args):
    from core.models.instance import Instance
    from core.email import send_deploy_failed_email
    try:
        logger.debug("deploy_failed task started at %s." % datetime.now())
        logger.info("task_uuid=%s" % task_uuid)
        result = app.AsyncResult(task_uuid)
        with allow_join_result():
            exc = result.get(propagate=False)
        err_str = "DEPLOYERROR::%s" % (result.traceback,)
        logger.error(err_str)
        driver = get_driver(driverCls, provider, identity)
        instance = driver.get_instance(instance_id)
        update_instance_metadata(driver, instance,
                                 data={'tmp_status': 'deploy_error'},
                                 replace=False)
        logger.debug("deploy_failed task finished at %s." % datetime.now())
    except Exception as exc:
        logger.warn(exc)
        deploy_failed.retry(exc=exc)


@task(name="deploy_to",
      max_retries=2,
      default_retry_delay=128,
      ignore_result=True)
def deploy_to(driverCls, provider, identity, instance_id, *args, **kwargs):
    try:
        logger.debug("deploy_to task started at %s." % datetime.now())
        driver = get_driver(driverCls, provider, identity)
        instance = driver.get_instance(instance_id)
        driver.deploy_to(instance, *args, **kwargs)
        logger.debug("deploy_to task finished at %s." % datetime.now())
    except Exception as exc:
        logger.warn(exc)
        deploy_to.retry(exc=exc)


@task(name="deploy_init_to",
      default_retry_delay=20,
      ignore_result=True,
      max_retries=3)
def deploy_init_to(driverCls, provider, identity, instance_id,
                   username=None, password=None, redeploy=False,
                   *args, **kwargs):
    try:
        logger.debug("deploy_init_to task started at %s." % datetime.now())
        driver = get_driver(driverCls, provider, identity)
        instance = driver.get_instance(instance_id)
        if not instance:
            logger.debug("Instance has been teminated: %s." % instance_id)
            return
        image_metadata = driver._connection\
                               .ex_get_image_metadata(instance.machine)
        deploy_chain = get_deploy_chain(driverCls, provider, identity,
                                        instance, password, redeploy)
        logger.debug("Starting deploy chain for: %s." % instance_id)
        deploy_chain.apply_async()
        #Can be really useful when testing.
        #if kwargs.get('delay'):
        #    async.get()
        logger.debug("deploy_init_to task finished at %s." % datetime.now())
    except SystemExit:
        logger.exception("System Exits are BAD! Find this and get rid of it!")
        raise Exception("System Exit called")
    except NonZeroDeploymentException as non_zero:
        logger.error(str(non_zero))
        logger.error(non_zero.__dict__)
        raise
    except Exception as exc:
        logger.warn(exc)
        deploy_init_to.retry(exc=exc)


def get_deploy_chain(driverCls, provider, identity, instance,
                     username=None, password=None, redeploy=False):
    instance_id = instance.id
    wait_active_task = wait_for_instance.s(
        instance_id, driverCls, provider, identity, "active")
    if not instance.ip:
        #Init the networking
        logger.debug("IP address missing -- add 'add floating IP' tasks..")
        network_meta_task = update_metadata.si(
            driverCls, provider, identity, instance_id,
            {'tmp_status': 'networking'})
        floating_task = add_floating_ip.si(
            driverCls, provider, identity, instance_id, delete_status=True)

    #Always deploy to the instance, but change what atmo-init does..
    deploy_meta_task = update_metadata.si(
        driverCls, provider, identity, instance_id,
        {'tmp_status': 'deploying'})
    deploy_task = _deploy_init_to.si(
        driverCls, provider, identity, instance_id,
        username, password, redeploy)
    deploy_task.link_error(
        deploy_failed.s(driverCls, provider, identity, instance_id))

    #Call additional Deployments
    check_shell_task = check_process_task.si(
        driverCls, provider, identity, instance_id, "shellinaboxd")
    check_vnc_task = check_process_task.si(
        driverCls, provider, identity, instance_id, "vnc")

    #Then remove the tmp_status
    if instance.extra['metadata'].get('iplant_suspend_fix'):
        replace = True
        final_update = instance.extra['metadata']
        final_update.pop('tmp_status')
        final_update.pop('iplant_suspend_fix')
    else:
        final_update = {'tmp_status': ''}
        replace = False
    remove_status_task = update_metadata.si(
        driverCls, provider, identity, instance_id,
        final_update, replace)

    #Finally email the user
    if not redeploy:
        email_task = _send_instance_email.si(
            driverCls, provider, identity, instance_id)
    ## Link the chain below this line.
    ##
    start_chain = wait_active_task
    if not instance.ip:
        # Task will start with networking
        # link networking to deploy..
        wait_active_task.link(network_meta_task)
        network_meta_task.link(floating_task)
        floating_task.link(deploy_meta_task)
    else:
        #Networking is ready, just deploy.
        wait_active_task.link(deploy_meta_task)

    deploy_meta_task.link(deploy_task)
    deploy_task.link(check_shell_task)
    check_shell_task.link(check_vnc_task)
    check_vnc_task.link(remove_status_task)
    if not redeploy:
        remove_status_task.link(email_task)
    return start_chain


@task(name="destroy_instance",
      default_retry_delay=15,
      ignore_result=True,
      max_retries=3)
def destroy_instance(instance_alias, core_identity_id):
    from service import instance as instance_service
    from rtwo.driver import OSDriver
    try:
        logger.debug("destroy_instance task started at %s." % datetime.now())
        node_destroyed = instance_service.destroy_instance(
            core_identity_id, instance_alias)
        core_identity = Identity.objects.get(id=core_identity_id)
        driver = get_esh_driver(core_identity)
        if isinstance(driver, OSDriver):
            #Spawn off the last two tasks
            logger.debug("OSDriver Logic -- Remove floating ips and check"
                         " for empty project")
            driverCls = driver.__class__
            provider = driver.provider
            identity = driver.identity
            instances = driver.list_instances()
            active = [driver._is_active_instance(inst) for inst in instances]
            if not active:
                logger.debug("Driver shows 0 of %s instances are active"
                             % (len(instances),))
                #For testing ONLY.. Test cases ignore countdown..
                if app.conf.CELERY_ALWAYS_EAGER:
                    logger.debug("Eager task waiting 1 minute")
                    time.sleep(60)
                destroy_chain = chain(
                    clean_empty_ips.subtask(
                        (driverCls, provider, identity),
                        immutable=True, countdown=5),
                    remove_empty_network.subtask(
                        (driverCls, provider, identity, core_identity_id),
                        immutable=True, countdown=60))
                destroy_chain()
            else:
                logger.debug("Driver shows %s of %s instances are active"
                             % (len(active), len(instances)))
                #For testing ONLY.. Test cases ignore countdown..
                if app.conf.CELERY_ALWAYS_EAGER:
                    logger.debug("Eager task waiting 15 seconds")
                    time.sleep(15)
                destroy_chain = \
                    clean_empty_ips.subtask(
                        (driverCls, provider, identity),
                        immutable=True, countdown=5).apply_async()
        logger.debug("destroy_instance task finished at %s." % datetime.now())
        return node_destroyed
    except Exception as exc:
        logger.exception(exc)
        destroy_instance.retry(exc=exc)


@task(name="deploy_script",
      default_retry_delay=32,
      time_limit=30*60,  # 30minute hard-set time limit.
      max_retries=10)
def deploy_script(driverCls, provider, identity, instance_id,
                  script, **celery_task_args):
    try:
        logger.debug("deploy_script task started at %s." % datetime.now())
        #Check if instance still exists
        driver = get_driver(driverCls, provider, identity)
        instance = driver.get_instance(instance_id)
        if not instance:
            logger.debug("Instance has been teminated: %s." % instance_id)
            return
        #TODO: Is this still necessary? What about times when we want to use
        # the adminPass? --Steve
        instance._node.extra['password'] = None

        kwargs = _generate_ssh_kwargs()
        kwargs.update({'deploy': script})
        driver.deploy_to(instance, **kwargs)
        logger.debug("deploy_script task finished at %s." % datetime.now())
    except DeploymentError as exc:
        logger.exception(exc)
        if isinstance(exc.value, NonZeroDeploymentException):
            #The deployment was successful, but the return code on one or more
            # steps is bad. Log the exception and do NOT try again!
            raise exc.value
        #TODO: Check if all exceptions thrown at this time
        #fall in this category, and possibly don't retry if
        #you hit the Exception block below this.
        deploy_script.retry(exc=exc)
    except Exception as exc:
        logger.exception(exc)
        deploy_script.retry(exc=exc)


@task(name="_deploy_init_to",
      default_retry_delay=32,
      time_limit=30*60,  # 30minute hard-set time limit.
      max_retries=10)
def _deploy_init_to(driverCls, provider, identity, instance_id,
                    username=None, password=None, token=None, redeploy=False,
                    **celery_task_args):
    try:
        logger.debug("_deploy_init_to task started at %s." % datetime.now())
        #Check if instance still exists
        driver = get_driver(driverCls, provider, identity)
        instance = driver.get_instance(instance_id)
        if not instance:
            logger.debug("Instance has been teminated: %s." % instance_id)
            return

        #NOTE: This is required to use ssh to connect.
        #TODO: Is this still necessary? What about times when we want to use
        # the adminPass? --Steve
        logger.info(instance.extra)
        instance._node.extra['password'] = None
        msd = init(instance, identity.user.username, password, token, redeploy)

        kwargs = _generate_ssh_kwargs()
        kwargs.update({'deploy': msd})
        driver.deploy_to(instance, **kwargs)
        _update_status_log(instance, "Deploy Finished")
        logger.debug("_deploy_init_to task finished at %s." % datetime.now())
    except DeploymentError as exc:
        logger.exception(exc)
        if isinstance(exc.value, NonZeroDeploymentException):
            #The deployment was successful, but the return code on one or more
            # steps is bad. Log the exception and do NOT try again!
            raise exc.value
        #TODO: Check if all exceptions thrown at this time
        #fall in this category, and possibly don't retry if
        #you hit the Exception block below this.
        _deploy_init_to.retry(exc=exc)
    except SystemExit as bad_ssh:
        logger.exception("ERROR: Someone has raised a SystemExit!")
        _deploy_init_to.retry(exc=bad_ssh)
    except Exception as exc:
        logger.exception(exc)
        _deploy_init_to.retry(exc=exc)


@task(name="check_process_task",
      max_retries=2,
      default_retry_delay=15)
def check_process_task(driverCls, provider, identity,
                       instance_alias, process_name, *args, **kwargs):
    """
    #NOTE: While this looks like a large number (250 ?!) of retries
    # we expect this task to fail often when the image is building
    # and large, uncached images can have a build time.
    """
    from core.models.instance import Instance
    try:
        logger.debug("check_process_task started at %s." % datetime.now())
        driver = get_driver(driverCls, provider, identity)
        instance = driver.get_instance(instance_alias)
        if not instance:
            return
        cp_script = check_process(process_name)
        kwargs.update({
            'ssh_key': ATMOSPHERE_PRIVATE_KEYFILE,
            'timeout': 120,
            'deploy': cp_script})
        #Execute the script
        driver.deploy_to(instance, **kwargs)
        #Parse the output and modify the CORE instance
        script_out = cp_script.stdout
        result = True if "1:" in script_out else False
        #NOTE: Throws Instance.DoesNotExist
        core_instance = Instance.objects.get(provider_alias=instance_alias)
        if "vnc" in process_name:
            core_instance.vnc = result
            core_instance.save()
        elif "shellinaboxd" in process_name:
            core_instance.shell = result
            core_instance.save()
        else:
            return result, script_out
        logger.debug("check_process_task finished at %s." % datetime.now())
    except Instance.DoesNotExist:
        logger.warn("check_process_task failed: Instance %s no longer exists"
                    % instance_alias)
    except Exception as exc:
        logger.exception(exc)
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
        logger.debug("update_metadata task started at %s." % datetime.now())
        driver = get_driver(driverCls, provider, identity)
        instance = driver.get_instance(instance_alias)
        if not instance:
            return
        return update_instance_metadata(
            driver, instance, data=metadata, replace=replace_metadata)
        logger.debug("update_metadata task finished at %s." % datetime.now())
    except Exception as exc:
        logger.exception(exc)
        update_metadata.retry(exc=exc)


# Floating IP Tasks
@task(name="add_floating_ip",
      #Defaults will not be used, see countdown call below
      default_retry_delay=15,
      max_retries=30)
def add_floating_ip(driverCls, provider, identity,
                    instance_alias, delete_status=True,
                    *args, **kwargs):
    #For testing ONLY.. Test cases ignore countdown..
    if app.conf.CELERY_ALWAYS_EAGER:
        logger.debug("Eager task waiting 15 seconds")
        time.sleep(15)
    try:
        logger.debug("add_floating_ip task started at %s." % datetime.now())
        #Remove unused floating IPs first, so they can be re-used
        driver = get_driver(driverCls, provider, identity)
        driver._clean_floating_ip()

        #assign if instance doesn't already have an IP addr
        instance = driver.get_instance(instance_alias)
        if not instance:
            logger.debug("Instance has been teminated: %s." % instance_alias)
            return None
        floating_ips = driver._connection.neutron_list_ips(instance)
        if floating_ips:
            floating_ip = floating_ips[0]["floating_ip_address"]
        else:
            floating_ip = driver._connection.neutron_associate_ip(
                instance, *args, **kwargs)["floating_ip_address"]
        _update_status_log(instance, "Networking Complete")
        #TODO: Implement this as its own task, with the result from
        #'floating_ip' passed in. Add it to the deploy_chain before deploy_to
        hostname = ""
        if floating_ip.startswith('128.196'):
            regex = re.compile(
                "(?P<one>[0-9]+)\.(?P<two>[0-9]+)\."
                "(?P<three>[0-9]+)\.(?P<four>[0-9]+)")
            r = regex.search(floating_ip)
            (one, two, three, four) = r.groups()
            hostname = "vm%s-%s.iplantcollaborative.org" % (three, four)
        else:
            # Find a way to convert new floating IPs to hostnames..
            hostname = floating_ip

        metadata_update = {
            'public-hostname': hostname,
            'public-ip': floating_ip
        }
        #NOTE: This is part of the temp change, should be removed when moving
        # to vxlan
        instance_ports = driver._connection.neutron_list_ports(device_id=instance.id)
        network = driver._connection.neutron_get_tenant_network()
        if instance_ports:
            for idx, fixed_ip_port in enumerate(instance_ports):
                fixed_ips = fixed_ip_port.get('fixed_ips',[])
                mac_addr = fixed_ip_port.get('mac_address')
                metadata_update['mac-address%s' % idx] = mac_addr
                metadata_update['port-id%s' % idx] = fixed_ip_port['id']
                metadata_update['network-id%s' % idx] = network['id']
        #EndNOTE:

        update_instance_metadata(
            driver, instance, data=metadata_update, replace=False)

        logger.info("Assigned IP:%s - Hostname:%s" % (floating_ip, hostname))
        #End
        logger.debug("add_floating_ip task finished at %s." % datetime.now())
        return {"floating_ip": floating_ip, "hostname": hostname}
    except Exception as exc:
        logger.exception("Error occurred while assigning a floating IP")
        #Networking can take a LONG time when an instance first launches,
        #it can also be one of those things you 'just miss' by a few seconds..
        #So we will retry 30 times using limited exp.backoff
        #Max Time: 53min
        countdown = min(2**current.request.retries, 128)
        add_floating_ip.retry(exc=exc,
                              countdown=countdown)


@task(name="clean_empty_ips", default_retry_delay=15,
      ignore_result=True, max_retries=6)
def clean_empty_ips(driverCls, provider, identity, *args, **kwargs):
    try:
        logger.debug("remove_floating_ip task started at %s." %
                     datetime.now())
        driver = get_driver(driverCls, provider, identity)
        ips_cleaned = driver._clean_floating_ip()
        logger.debug("remove_floating_ip task finished at %s." %
                     datetime.now())
        return ips_cleaned
    except Exception as exc:
        logger.warn(exc)
        clean_empty_ips.retry(exc=exc)


# project Network Tasks
@task(name="add_os_project_network",
      default_retry_delay=15,
      ignore_result=True,
      max_retries=6)
def add_os_project_network(core_identity, *args, **kwargs):
    try:
        logger.debug("add_os_project_network task started at %s." %
                     datetime.now())
        account_driver = get_account_driver(core_identity.provider)
        account_driver.create_network(core_identity)
        logger.debug("add_os_project_network task finished at %s." %
                     datetime.now())
    except Exception as exc:
        add_os_project_network.retry(exc=exc)


@task(name="remove_empty_network",
      default_retry_delay=60,
      max_retries=1)
def remove_empty_network(
        driverCls, provider, identity,
        core_identity_id,
        *args, **kwargs):
    try:
        #For testing ONLY.. Test cases ignore countdown..
        if app.conf.CELERY_ALWAYS_EAGER:
            logger.debug("Eager task waiting 1 minute")
            time.sleep(60)
        logger.debug("remove_empty_network task started at %s." %
                     datetime.now())

        logger.debug("CoreIdentity(id=%s)" % core_identity_id)
        core_identity = Identity.objects.get(id=core_identity_id)
        driver = get_driver(driverCls, provider, identity)
        instances = driver.list_instances()
        active_instances = any(
                driver._is_active_instance(instance) for
                instance in instances)
        #If instances are active, we are done..
        if not active_instances:
            inactive_instances = all(
                    driver._is_inactive_instance(
                    instance) for instance in instances)
            #Inactive instances: An instance that is 'stopped' or 'suspended'
            #Inactive instances, True: Remove network, False
            remove_network = not inactive_instances
            #Check for project network
            os_acct_driver = get_account_driver(core_identity.provider)
            logger.info("No active instances. Removing project network"
                        "from %s" % core_identity)
            os_acct_driver.delete_network(core_identity,
                                          remove_network=remove_network)
            if remove_network:
                #Sec. group can't be deleted if instances are suspended
                # when instances are suspended we pass remove_network=False
                os_acct_driver.delete_security_group(core_identity)
            return True
        logger.debug("remove_empty_network task finished at %s." %
                     datetime.now())
        return False
    except Exception as exc:
        logger.exception("Exception occurred project network is empty")


@task(name="check_image_membership")
def check_image_membership():
    try:
        logger.debug("check_image_membership task started at %s." %
                     datetime.now())
        update_membership()
        logger.debug("check_image_membership task finished at %s." %
                     datetime.now())
    except Exception as exc:
        logger.exception('Error during check_image_membership task')
        check_image_membership.retry(exc=exc)

@task(name="update_membership_for", queue="celery_periodic")
def update_membership_for(provider_id):
    from core.models import Provider, ProviderMachine
    provider = Provider.objects.get(id=provider_id)
    if not provider.is_active():
        return
    if provider.type.name.lower() == 'openstack':
        acct_driver = get_account_driver(provider)
    else:
        logger.warn("Encountered unknown ProviderType:%s, expected"
                    " [Openstack] " % (provider.type.name,))
        return
    images = acct_driver.list_all_images()
    changes = 0
    for img in images:
        pm = ProviderMachine.objects.filter(identifier=img.id,
                                            provider=provider)
        if not pm or len(pm) > 1:
            logger.debug("pm filter is bad!")
            logger.debug(pm)
            return
        else:
            pm = pm[0]
        app_manager = pm.application.applicationmembership_set
        if not img.is_public:
            #Lookup members
            image_members = acct_driver.image_manager.shared_images_for(
                image_id=img.id)
            #add machine to each member
            #(Who owns the cred:ex_project_name) in MachineMembership
            #for member in image_members:
        else:
            members = app_manager.all()
            #if MachineMembership exists, remove it (No longer private)
            if members:
                logger.info("Application for PM:%s used to be private."
                            " %s Users membership has been revoked. "
                            % (img.id, len(members)))
                changes += len(members)
                members.delete()
    logger.info("Total Updates to machine membership:%s" % changes)

@task(name="update_membership")
def update_membership():
    from service.accounts.eucalyptus import AccountDriver as EucaAcctDriver
    for provider in Provider.objects.all():
        update_membership_for.apply_async( args=[provider.id])


def active_instances(instances):
    tested_instances = {}
    for instance in instances:
        results = test_instance_links(instance.alias, instance.ip)
        tested_instances.update(results)
    return tested_instances


def test_instance_links(alias, uri):
    from rtwo.linktest import test_link
    if uri is None:
        return {alias: {'vnc': False, 'shell': False}}
    shell_address = '%s/shell/%s/' % (settings.SERVER_URL, uri)
    try:
        shell_success = test_link(shell_address)
    except Exception, e:
        logger.exception("Bad shell address: %s" % shell_address)
        shell_success = False
    vnc_address = 'http://%s:5904' % uri
    try:
        vnc_success = test_link(vnc_address)
    except Exception, e:
        logger.exception("Bad vnc address: %s" % vnc_address)
        vnc_success = False
    return {alias: {'vnc': vnc_success, 'shell': shell_success}}


def update_links(instances):
    from core.models import Instance
    updated = []
    linktest_results = active_instances(instances)
    for (instance_id, link_results) in linktest_results.items():
        try:
            update = False
            instance = Instance.objects.get(provider_alias=instance_id)
            if link_results['shell'] != instance.shell:
                logger.debug('Change Instance %s shell %s-->%s' %
                             (instance, instance.shell,
                              link_results['shell']))
                instance.shell = link_results['shell']
                update = True
            if link_results['vnc'] != instance.vnc:
                logger.debug('Change Instance %s VNC %s-->%s' %
                             (instance, instance.vnc,
                              link_results['vnc']))
                instance.vnc = link_results['vnc']
                update = True
            if update:
                instance.save()
                updated.append(instance)
        except Instance.DoesNotExist:
            continue
    logger.debug("Instances updated: %d" % len(updated))
    return updated
