"""
Tasks for driver operations.
"""
import re

from operator import attrgetter
from django.conf import settings
from django.utils.timezone import datetime
import time

from celery import chain
from celery.decorators import task
from celery.task import current
from celery.result import allow_join_result
from celery.task.schedules import crontab
from libcloud.compute.types import Provider, NodeState, DeploymentError

from atmosphere.celery import app

from threepio import logger
from rtwo.exceptions import NonZeroDeploymentException

from core.email import send_instance_email
from core.ldap import get_uid_number as get_unique_number
from service.instance import update_instance_metadata
from core.models.identity import Identity
from core.models.profile import UserProfile

from service.driver import get_driver
from service.deploy import init


@task(name="print_debug")
def print_debug():
    log_str = "print_debug task finished at %s." % datetime.now()
    print log_str
    logger.debug(log_str)

@task(name="add_fixed_ip",
        ignore_result=True,
        default_retry_delay=15,
        max_retries=15)
def add_fixed_ip(driverCls, provider, identity, instance_id):
    from service import instance as instance_service
    try:
        logger.debug("add_fixed_ip task started at %s." % datetime.now())
        driver = get_driver(driverCls, provider, identity)
        instance = driver.get_instance(instance_id)
        if not instance:
            logger.debug("Instance has been teminated: %s." % instance_id)
            return None
        i_status = instance._node.extra['status']
        i_task = instance._node.extra['task']
        if i_status not in ['active', 'suspended'] or i_task:
                    raise Exception("Instance %s Status %s Task %s - Not Ready"
                                    % (instance.id, i_status, i_task))
        if instance._node.private_ips:
            return instance
        network_id = instance_service._convert_network_name(
                driver, instance)
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
    from api import get_esh_driver
    from service.accounts.openstack import AccountDriver as\
        OSAccountDriver

    identities = Identity.objects.filter(
        provider__type__name__iexact='openstack',
        provider__active=True)
    identities = sorted(
       identities, key=lambda ident: attrgetter(ident.provider.type.name,
                                                ident.created_by.username))
    os_acct_driver = None
    total = len(identities)
    for idx, core_identity in enumerate(identities):
        try:
            #Initialize the drivers
            driver = get_esh_driver(core_identity)
            if not isinstance(driver, OSDriver):
                continue
            if not os_acct_driver or\
                    os_acct_driver.core_provider != core_identity.provider:
                os_acct_driver = OSAccountDriver(core_identity.provider)
                logger.info("Initialized account driver")
            # Get useful info
            creds = core_identity.get_credentials()
            tenant_name = creds['ex_tenant_name']
            logger.info("Checking Identity %s/%s - %s"
                        % (idx+1, total, tenant_name))
            # Attempt to clean floating IPs
            num_ips_removed = driver._clean_floating_ip()
            if num_ips_removed:
                logger.debug("Removed %s ips from OpenStack Tenant %s"
                             % (num_ips_removed, tenant_name))
            #Test for active/inactive instances
            instances = driver.list_instances()
            active = any(driver._is_active_instance(inst) for inst in instances)
            inactive = all(driver._is_inactive_instance(inst) for inst in instances)
            if active and not inactive:
                #User has >1 active instances AND not all instances inactive
                pass
            elif os_acct_driver.network_manager.get_network_id(
                    os_acct_driver.network_manager.neutron, '%s-net' % tenant_name):
                #User has 0 active instances OR all instances are inactive
                #Network exists, attempt to dismantle as much as possible
                remove_network = not inactive
                logger.info("Removing project network %s for %s"
                            % (remove_network, tenant_name))
                if remove_network:
                    #Sec. group can't be deleted if instances are suspended
                    # when instances are suspended we pass remove_network=False
                    os_acct_driver.delete_security_group(core_identity)
                    os_acct_driver.delete_network(core_identity,
                            remove_network=remove_network)
            else:
                #logger.info("No Network found. Skipping %s" % tenant_name)
                pass
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
                   password=None, redeploy=False, *args, **kwargs):
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
        deploy_chain.apply_async()
        #Can be really useful when testing.
        #if kwargs.get('delay'):
        #    async.get()
        logger.debug("deploy_init_to task finished at %s." % datetime.now())
    except NonZeroDeploymentException:
        raise
    except Exception as exc:
        logger.warn(exc)
        deploy_init_to.retry(exc=exc)

def get_deploy_chain(driverCls, provider, identity,
                     instance, password, redeploy=False):
    instance_id = instance.id
    if not instance.ip:
        #Init the networking
        logger.debug("IP address missing")
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
        driverCls, provider, identity, instance_id, password, redeploy)
    deploy_task.link_error(
        deploy_failed.s(driverCls, provider, identity, instance_id))
    remove_status_task = update_metadata.si(
            driverCls, provider, identity, instance_id,
            {'tmp_status': ''})

    ## Link the chain below this line.
    ##
    if not instance.ip:
        # Task will start with networking
        # link networking to deploy..
        start_chain = network_meta_task
        network_meta_task.link(floating_task)
        floating_task.link(deploy_meta_task)
    else:
        #Networking is ready, just deploy.
        start_chain = deploy_meta_task

    deploy_meta_task.link(deploy_task)
    deploy_task.link(remove_status_task)
    if not redeploy:
        email_task = _send_instance_email.si(
                driverCls, provider, identity, instance_id)
        remove_status_task.link(email_task)
    return start_chain


@task(name="destroy_instance",
      default_retry_delay=15,
      ignore_result=True,
      max_retries=3)
def destroy_instance(core_identity_id, instance_alias):
    from service import instance as instance_service
    from rtwo.driver import OSDriver
    from api import get_esh_driver
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


@task(name="_deploy_init_to",
      default_retry_delay=32,
      time_limit=30*60, #30minute hard-set time limit.
      max_retries=10)
def _deploy_init_to(driverCls, provider, identity, instance_id,
                    password=None, redeploy=False, **celery_task_args):
    try:
        logger.debug("_deploy_init_to task started at %s." % datetime.now())
        #Check if instance still exists
        driver = get_driver(driverCls, provider, identity)
        instance = driver.get_instance(instance_id)
        if not instance:
            logger.debug("Instance has been teminated: %s." % instance_id)
            return
        #NOTE: This is NOT the password passed by argument
        #Deploy with no password to use ssh keys
        logger.info(instance.extra)
        instance._node.extra['password'] = None
        kwargs = {}
        private_key = "/opt/dev/atmosphere/extras/ssh/id_rsa"
        kwargs.update({'ssh_key': private_key})
        kwargs.update({'timeout': 120})
        msd = init(instance, identity.user.username, password, redeploy)
        kwargs.update({'deploy': msd})
        driver.deploy_to(instance, **kwargs)
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
    except Exception as exc:
        logger.exception(exc)
        _deploy_init_to.retry(exc=exc)

@task(name="update_metadata", max_retries=250, default_retry_delay=15)
def update_metadata(driverCls, provider, identity, instance_alias, metadata):
    """
    #NOTE: While this looks like a large number (250 ?!) of retries
    # we expect this task to fail often when the image is building
    # and large, uncached images can have a build time 
    """
    try:
        logger.debug("update_metadata task started at %s." % datetime.now())
        driver = get_driver(driverCls, provider, identity)
        instance = driver.get_instance(instance_alias)
        if not instance:
            return
        #NOTE: This task will only be executed in TEST mode
        if app.conf.CELERY_ALWAYS_EAGER:
            eager_update_metadata(driver, instance, metadata)
        return update_instance_metadata(
            driver, instance, data=metadata, replace=False)
        logger.debug("update_metadata task finished at %s." % datetime.now())
    except Exception as exc:
        logger.exception(exc)
        update_metadata.retry(exc=exc)

def eager_update_metadata(driver, instance, metadata):
    """
    Used for TESTING ONLY. NEVER called in normal celery operation.
    """
    while 1:
        #Check if instance is terminated or no longer building.
        if not instance or instance.extra['status'] != 'build':
            break
        #Wait 1min try again
        wait_time = 1*60
        logger.info("Always Eager Detected and instance is not active"
                    ". Will wait 1 minute and check again to avoid"
                    " stack overflow from immediately retrying.."
                    )
        time.sleep(wait_time*60)
        # Update reference for the instance to see if its 'done'
        instance = driver.get_instance(instance_id)
    return update_instance_metadata(
        driver, instance, data=metadata, replace=False)

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
        update_instance_metadata(driver, instance, data={
            'public-hostname': hostname,
            'public-ip':floating_ip}, replace=False)

        logger.info("Assigned IP:%s - Hostname:%s" % (floating_ip, hostname))
        #End
        logger.debug("add_floating_ip task finished at %s." % datetime.now())
        return {"floating_ip":floating_ip, "hostname":hostname}
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
        from rtwo.accounts.openstack import AccountDriver as OSAccountDriver
        account_driver = OSAccountDriver(core_identity.provider)
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
        active_instances = False
        for instance in instances:
            if driver._is_active_instance(instance):
                active_instances = True
                break
        if not active_instances:
            inactive_instances = all(driver._is_inactive_instance(
                instance) for instance in instances)
            #Inactive instances, True: Remove network, False
            remove_network = not inactive_instances
            #Check for project network
            from service.accounts.openstack import AccountDriver as\
                OSAccountDriver
            os_acct_driver = OSAccountDriver(core_identity.provider)
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
        logger.exception("Failed to check if project network is empty")
        remove_empty_network.retry(exc=exc)


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


def update_membership():
    from core.models import ApplicationMembership, Provider, ProviderMachine
    from service.accounts.openstack import AccountDriver as OSAcctDriver
    from service.accounts.eucalyptus import AccountDriver as EucaAcctDriver
    for provider in Provider.objects.all():
        if not provider.is_active():
            return []
        if provider.type.name.lower() == 'openstack':
            driver = OSAcctDriver(provider)
        else:
            logger.warn("Encountered unknown ProviderType:%s, expected"
                        " [Openstack]")
            continue
        images = driver.list_all_images()
        changes = 0
        for img in images:
            pm = ProviderMachine.objects.filter(identifier=img.id,
                                                provider=provider)
            if not pm:
                continue
            app_manager = pm.application.applicationmembership_set
            if img.is_public == False:
                #Lookup members
                image_members = accts.image_manager.shared_images_for(
                        image_id=img.id)
                #add machine to each member (Who owns the cred:ex_project_name) in MachineMembership
                #for member in image_members:
            else:
                members = app_manager.all()
                if members:
                    logger.info("Application for PM:%s used to be private."
                                " %s Users membership has been revoked. "
                                % (img.id, len(members)))
                    changes += len(members)
                    members.delete()
                #if MachineMembership exists, remove it (No longer private)
    logger.info("Total Updates to machine membership:%s" % changes)
    return changes


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
