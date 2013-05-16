from datetime import datetime

from celery.decorators import task
from celery.task import current
from celery import chain

from threepio import logger

from core.email import send_instance_email
from core.models.instance import update_instance_metadata

# Utility methods and tasks
def get_driver(driverCls, provider, identity):
    logger.debug("getting driver...")
    from service import compute
    compute.initialize()
    driver = driverCls(provider, identity)
    if driver:
        logger.debug("created driver.")
        return driver

@task(name="_send_instance_email",
      default_retry_delay=10,
      ignore_result=True,
      max_retries=2)
def _send_instance_email(driverCls, provider, identity, instance_id):
    try:
        logger.debug("_send_instance_email task started at %s." % datetime.now())
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
                            instance.ip,
                            created,
                            username)
        logger.debug("_send_instance_email task finished at %s." % datetime.now())
    except Exception as exc:
        logger.warn(exc)
        _send_instance_email.retry(exc=exc)


# Deploy and Destroy tasks
@task(name="deploy_to",
      max_retries=2,
      default_retry_delay=120,
      ignore_result=True)
def deploy_to(driverCls, provider, identity, instance, *args, **kwargs):
    try:
        logger.debug("deploy_to task started at %s." % datetime.now())
        driver = get_driver(driverCls, provider, identity)
        driver.deploy_init_to(instance, *args, **kwargs)
        logger.debug("deploy_to task finished at %s." % datetime.now())
    except Exception as exc:
        logger.warn(exc)
        deploy_to.retry(exc=exc)

@task(name="deploy_init_to",
      default_retry_delay=60,
      ignore_result=True,
      max_retries=1)
def deploy_init_to(driverCls, provider, identity, instance_id, *args, **kwargs):
    try:
        logger.debug("deploy_init_to task started at %s." % datetime.now())
        driver = get_driver(driverCls, provider, identity)
        instance = driver.get_instance(instance_id)
        image_metadata = driver._connection.ex_get_image_metadata(instance.machine)
        image_already_deployed = image_metadata.get("deployed")
        if not instance.ip and not image_already_deployed:
            logger.debug("Chain -- Floating_ip + deploy_init + email")
            chain(add_floating_ip.si(driverCls,
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
                                          instance_id)).apply_async()
        elif not image_already_deployed:
            logger.debug("Chain -- deploy_init + email")
            chain(_deploy_init_to.si(driverCls,
                                     provider,
                                     identity,
                                     instance_id),
                  _send_instance_email.si(driverCls,
                                          provider,
                                          identity,
                                          instance_id)).apply_async()
        elif not instance.ip:
            logger.debug("Chain -- Floating_ip + email")
            chain(add_floating_ip.si(driverCls,
                                     provider,
                                     identity,
                                     instance_id, delete_status=True),
                  _send_instance_email.si(driverCls,
                                          provider,
                                          identity,
                                          instance_id)).apply_async()
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
      max_retries=6)
def destroy_instance(driverCls, provider, identity, instance_alias):
    try:
        logger.debug("destroy_instance task started at %s." % datetime.now())
        driver = get_driver(driverCls, provider, identity)
        instance = driver.get_instance(instance_alias)
        from service.driver import OSDriver
        if instance:
            #First disassociate
            if isinstance(driver, OSDriver):
                driver._connection.ex_disassociate_floating_ip(instance)
            #Then destroy
            node_destroyed = driver._connection.destroy_node(instance)
        else:
            logger.debug("Instance already deleted: %s." % instance.id)
        if isinstance(driver, OSDriver):
            #Spawn off the last two tasks
            logger.debug("OSDriver Logic -- Remove floating ips and check"
            " for empty project")
            chain(_remove_floating_ip.subtask((driverCls,
                                     provider,
                                     identity), immutable=True, countdown=5),
                  _check_empty_project_network.subtask((driverCls,
                                     provider,
                                     identity), immutable=True, countdown=60)
                 ).apply_async()

        logger.debug("destroy_instance task finished at %s." % datetime.now())
        return node_destroyed
    except Exception as exc:
        logger.warn(exc)
        destroy_instance.retry(exc=exc)

@task(name="_deploy_init_to",
      default_retry_delay=120,
      ignore_result=True,
      max_retries=2)
def _deploy_init_to(driverCls, provider, identity, instance_id):
    try:
        logger.debug("_deploy_init_to task started at %s." % datetime.now())

        #Check if instance still exists
        driver = get_driver(driverCls, provider, identity)
        instance = driver.get_instance(instance_id)
        if not instance:
            logger.debug("Instance already deleted: %s." % instance_id)
            return

        update_instance_metadata(driver, instance,
                                 data={'tmp_status':'deploying'},
                                 replace=False)

        #Deploy with no password to use ssh keys
        logger.info(instance.extra)
        instance._node.extra['password'] = None
        driver.deploy_init_to(instance)

        update_instance_metadata(driver, instance,
                                 data={'tmp_status':''},
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
      max_retries=10)
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

        update_instance_metadata(driver, instance,
                                 data={'tmp_status':'networking'},
                                 replace=False)

        if not instance.ip:
            driver._add_floating_ip(instance, *args, **kwargs)
        else:
            logger.debug("public ip already found! %s" % instance.ip)

        #Useful for chaining floating-ip + Deployment without returning
        #a 'fully active' state
        if delete_status:
            update_instance_metadata(driver, instance,
                                     data={'tmp_status':''},
                                     replace=False)
        logger.debug("add_floating_ip task finished at %s." % datetime.now())
    except Exception as exc:
        logger.exception("Error occurred while assigning a floating IP")
        #Networking can take a LONG time when an instance first launches,
        #it can also be one of those things you 'just miss' by a few seconds..
        #So we will retry 10 times using exp.backoff
        #Max Time: 10.6min
        countdown = min(2**current.request.retries, 128)
        add_floating_ip.retry(exc=exc,
                              countdown=countdown)

@task(name="_remove_floating_ip",
      default_retry_delay=15,
      ignore_result=True,
      max_retries=6)
def _remove_floating_ip(driverCls, provider, identity, *args, **kwargs):
    try:
        logger.debug("remove_floating_ip task started at %s." % datetime.now())
        driver = get_driver(driverCls, provider, identity)
        driver._clean_floating_ip()
        logger.debug("remove_floating_ip task finished at %s." % datetime.now())
    except Exception as exc:
        logger.warn(exc)
        _remove_floating_ip.retry(exc=exc)


# project Network Tasks
@task(name="add_os_project_network",
      default_retry_delay=15,
      ignore_result=True,
      max_retries=6)
def add_os_project_network(username, *args, **kwargs):
    try:
        logger.debug("add_os_project_network task started at %s." % datetime.now())
        from service.accounts.openstack import AccountDriver as OSAccountDriver
        account_driver = OSAccountDriver()
        password = account_driver.hashpass(username)
        project_name = account_driver.get_project_name_for(username)
        account_driver.network_manager.create_project_network(
            username,
            password,
            project_name,
            **settings.OPENSTACK_NETWORK_ARGS)
        logger.debug("add_os_project_network task finished at %s." % datetime.now())
    except Exception as exc:
        add_os_project_network.retry(exc=exc)

@task(name="_check_empty_project_network",
      default_retry_delay=60,
      ignore_result=True,
      max_retries=1)
def _check_empty_project_network(driverCls, provider, identity, *args, **kwargs):
    try:
        logger.debug("_check_empty_project_network task started at %s." % datetime.now())
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
            os_acct_driver = OSAccountDriver()
            username = identity.user.username
            project_name = username
            logger.info("No active instances. Removing project network"
                    "from %s"
                    % username)
            os_acct_driver.network_manager.delete_project_network(username,
                    project_name)
        logger.debug("_check_empty_project_network task finished at %s." % datetime.now())
    except Exception as exc:
        logger.warn(exc)
        _check_empty_project_network.retry(exc=exc)
