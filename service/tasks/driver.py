"""
Tasks for driver operations.
"""
from datetime import datetime

from celery.decorators import task
from celery.task import current
from celery import chain

from threepio import logger

from core.email import send_instance_email
from core.ldap import get_uid_number as get_unique_number
from core.models.instance import update_instance_metadata
from core.models.identity import Identity

from service.driver import get_driver

@task(name="_send_instance_email",
      default_retry_delay=10,
      ignore_result=True,
      max_retries=2)
def _send_instance_email(driverCls, provider, identity, instance_id):
    try:
        logger.debug("_send_instance_email task started at %s." %
                     datetime.now())
        driver = get_driver(driverCls, provider, identity)
        instance = driver.get_instance(instance_id)
        #Breakout if instance has been deleted at this point
        if not instance:
            return
        username = identity.user.username
        created = datetime.strptime(instance.extra['created'],
                                    "%Y-%m-%dT%H:%M:%SZ")
        send_instance_email(username,
                            instance.id,
                            instance.name,
                            instance.ip,
                            created,
                            username)
        logger.debug("_send_instance_email task finished at %s." %
                     datetime.now())
    except Exception as exc:
        logger.warn(exc)
        _send_instance_email.retry(exc=exc)


# Deploy and Destroy tasks
@task(name="deploy_failed",
      max_retries=2,
      default_retry_delay=128,
      ignore_result=True)
def deploy_failed(driverCls, provider, identity, instance_id, task_uuid):
    try:
        logger.debug("deploy_failed task started at %s." % datetime.now())
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
                   *args, **kwargs):
    try:
        logger.debug("deploy_init_to task started at %s." % datetime.now())
        driver = get_driver(driverCls, provider, identity)
        instance = driver.get_instance(instance_id)
        if not instance:
            return
        image_metadata = driver._connection\
                               .ex_get_image_metadata(instance.machine)
        image_already_deployed = image_metadata.get("deployed")
        if not instance.ip and not image_already_deployed:
            logger.debug("Chain -- Floating_ip + deploy_init + email")
            cflow = chain(add_floating_ip.si(driverCls,
                                             provider,
                                             identity,
                                             instance_id, delete_status=False),
                          _deploy_init_to.si(driverCls,
                                             provider,
                                             identity,
                                             instance_id),
                          _send_instance_email.si(driverCls,
                                                  provider,
                                                  identity,
                                                  instance_id))
            cflow(link_error=deploy_failed.s((driverCls, provider, identity,
                                              instance_id,))),
        elif not image_already_deployed:
            logger.debug("Chain -- deploy_init + email")
            cflow = chain(_deploy_init_to.si(driverCls,
                                             provider,
                                             identity,
                                             instance_id),
                          _send_instance_email.si(driverCls,
                                                  provider,
                                                  identity,
                                                  instance_id))
            cflow(link_error=deploy_failed.s((driverCls, provider, identity,
                                              instance_id,))),
        elif not instance.ip:
            logger.debug("Chain -- Floating_ip + email")
            cflow = chain(add_floating_ip.si(driverCls,
                                             provider,
                                             identity,
                                             instance_id, delete_status=True),
                          _send_instance_email.si(driverCls,
                                                  provider,
                                                  identity,
                                                  instance_id))
            cflow()
        else:
            logger.debug("delay -- email")
            _send_instance_email.delay(driverCls,
                                       provider,
                                       identity,
                                       instance_id)
        logger.debug("deploy_init_to task finished at %s." % datetime.now())
    except Exception as exc:
        logger.warn(exc)
        deploy_init_to.retry(exc=exc)


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
        node_destroyed = instance_service.destroy_instance(core_identity_id, instance_alias)
        core_identity = Identity.objects.get(id=core_identity_id)
        driver = get_esh_driver(core_identity)
        if isinstance(driver, OSDriver):
            #Spawn off the last two tasks
            logger.debug("OSDriver Logic -- Remove floating ips and check"
                         " for empty project")
            driverCls = driver.__class__
            provider = driver.provider
            identity = driver.identity
            cflow = chain(clean_empty_ips
                          .subtask((driverCls,
                                    provider,
                                    identity),
                                   immutable=True,
                                   countdown=5),
                          remove_empty_network
                          .subtask((driverCls,
                                    provider,
                                    identity,
                                    core_identity_id),
                                   immutable=True,
                                   countdown=60))
            cflow()
        logger.debug("destroy_instance task finished at %s." % datetime.now())
        return node_destroyed
    except Exception as exc:
        logger.exception(exc)
        destroy_instance.retry(exc=exc)


@task(name="_deploy_init_to",
      default_retry_delay=32,
      ignore_result=True,
      max_retries=10)
def _deploy_init_to(driverCls, provider, identity, instance_id):
    try:
        logger.debug("_deploy_init_to task started at %s." % datetime.now())

        #Check if instance still exists
        driver = get_driver(driverCls, provider, identity)
        instance = driver.get_instance(instance_id)
        if not instance:
            logger.debug("Instance has been teminated: %s." % instance_id)
            return

        update_instance_metadata(driver, instance,
                                 data={'tmp_status': 'deploying'},
                                 replace=False)

        #Deploy with no password to use ssh keys
        logger.info(instance.extra)
        instance._node.extra['password'] = None
        driver.deploy_init_to(instance)

        update_instance_metadata(driver, instance,
                                 data={'tmp_status': ''},
                                 replace=False)
        logger.debug("_deploy_init_to task finished at %s." % datetime.now())
    except Exception as exc:
        logger.exception(exc)
        _deploy_init_to.retry(exc=exc)


# Floating IP Tasks
@task(name="add_floating_ip",
      #Defaults will not be used, see countdown call below
      default_retry_delay=15,
      ignore_result=True,
      max_retries=30)
def add_floating_ip(driverCls, provider, identity,
                    instance_alias, delete_status=True,
                    *args, **kwargs):
    try:
        logger.debug("add_floating_ip task started at %s." % datetime.now())
        #Remove unused floating IPs first, so they can be re-used
        driver = get_driver(driverCls, provider, identity)
        driver._clean_floating_ip()

        #assign if instance doesn't already have an IP addr
        instance = driver.get_instance(instance_alias)
        if not instance:
            return
        #TODO: Don't even attempt this until we are out of build
        update_instance_metadata(driver, instance,
                                 data={'tmp_status': 'networking'},
                                 replace=False)

        driver._connection.neutron_associate_ip(instance, *args, **kwargs)

        #Useful for chaining floating-ip + Deployment without returning
        #a 'fully active' state
        if delete_status:
            update_instance_metadata(driver, instance,
                                     data={'tmp_status': ''},
                                     replace=False)
        logger.debug("add_floating_ip task finished at %s." % datetime.now())
    except Exception as exc:
        logger.exception("Error occurred while assigning a floating IP")
        #Networking can take a LONG time when an instance first launches,
        #it can also be one of those things you 'just miss' by a few seconds..
        #So we will retry 30 times using limited exp.backoff
        #Max Time: 53min
        countdown = min(2**current.request.retries, 128)
        add_floating_ip.retry(exc=exc,
                              countdown=countdown)

@task(name="clean_empty_ips",
      default_retry_delay=15,
      ignore_result=True,
      max_retries=6)
def clean_empty_ips(driverCls, provider, identity, *args, **kwargs):
    try:
        logger.debug("remove_floating_ip task started at %s." %
                     datetime.now())
        driver = get_driver(driverCls, provider, identity)
        driver._clean_floating_ip()
        logger.debug("remove_floating_ip task finished at %s." %
                     datetime.now())
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
      ignore_result=True,
      max_retries=1)
def remove_empty_network(
        driverCls, provider, identity,
        core_identity_id,
        *args, **kwargs):
    try:
        logger.debug("remove_empty_network task started at %s." %
                     datetime.now())

        logger.debug("Params - %s" % core_identity_id)
        core_identity = Identity.objects.get(id=core_identity_id)
        driver = get_driver(driverCls, provider, identity)
        instances = driver.list_instances()
        active_instances = False
        for instance in instances:
            if driver._is_active_instance(instance):
                active_instances = True
                break
        if not active_instances:
            #Check for project network
            from service.accounts.openstack import AccountDriver as\
                OSAccountDriver
            os_acct_driver = OSAccountDriver(core_identity.provider)
            logger.info("No active instances. Removing project network"
                        "from %s" % core_identity)
            os_acct_driver.delete_network(core_identity)
            os_acct_driver.delete_security_group(core_identity)
            return True
        logger.debug("remove_empty_network task finished at %s." %
                     datetime.now())
        return False
    except Exception as exc:
        logger.exception("Failed to check if project network is empty")
        remove_empty_network.retry(exc=exc)
