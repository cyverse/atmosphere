"""
Tasks for driver operations.
NOTE: At this point create options do not have a hard-set requirement for 'CoreIdentity'
Delete/remove operations do. This should be investigated further..
"""
from operator import attrgetter
import sys
import re
import time
from django.db import IntegrityError
from django.db.models import Q
from django.conf import settings
from django.utils.timezone import datetime, timedelta
from celery.decorators import task
from celery.exceptions import MaxRetriesExceededError
from celery.task import current
from celery.result import allow_join_result, AsyncResult
from celery import chain
from celery import current_app as app
from rtwo.exceptions import LibcloudInvalidCredsError, LibcloudBadResponseError
from rtwo.exceptions import NonZeroDeploymentException, NeutronBadRequest
from threepio import celery_logger, status_logger, logger

from core.email import send_instance_email
from core.models.deploy_record import DeployRecord
from core.models.boot_script import get_scripts_for_instance
from core.models.instance import Instance
from core.models.instance_history import InstanceStatusHistory
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
from service.networking import _generate_ssh_kwargs


@task(name="wait_for_instance", max_retries=120, default_retry_delay=15)
def wait_for_instance(instance_alias,
                      driverCls,
                      provider,
                      identity,
                      status_query,
                      skip_final_status=False):
    """
    Queries the cloud until the instance's status is found in the status_query

    skip_final_status=True is used when a deploy is waiting for an instance to
    get to active, but it doesn't want an active status to be created, which
    would cause clients to believe instance is in a final state
    """
    from core.models.instance import convert_esh_instance
    status_query = status_query if isinstance(status_query,
                                              list) else [status_query]

    class InstanceStatusNotReadyException(Exception):
        pass

    try:
        celery_logger.debug("wait_for task started at %s." % datetime.now())
        driver = get_driver(driverCls, provider, identity)
        instance = driver.get_instance(instance_alias)
        if not instance:
            celery_logger.debug(
                "Instance has been terminated: %s." % instance_alias)
            return False
        identity = Identity.objects.get(
            instance__provider_alias=instance_alias)
        status = instance.extra['status']
        task = instance.extra['task']

        if not task and status in status_query and not skip_final_status:
            convert_esh_instance(driver, instance, identity.provider.uuid,
                                 identity.uuid, identity.created_by)

        if task:
            raise InstanceStatusNotReadyException(
                "Instance ({}) is not ready. Waiting for task to complete: {}".
                format(instance_alias, task))
        elif status not in status_query:
            raise InstanceStatusNotReadyException(
                "Instance ({}) is not ready. Expected one of {}. But got {}".
                format(instance_alias, str(status_query), status))

    except InstanceStatusNotReadyException as exc:
        celery_logger.exception(exc)
        wait_for_instance.retry(exc=exc)
    except Exception as exc:
        wait_for_instance.retry(exc=exc)


@task(name="add_fixed_ip",
      ignore_result=True,
      default_retry_delay=15,
      max_retries=1)
# UNCOMMENT ME CONNOR
# max_retries=15)
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
        assert instance, "Instance no longer exists: {}".format(instance_id)

        update_instance_status(instance_id, "networking", "adding fixed ip")
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

        network_id = _get_network_id(network_driver, instance)

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


@task(name="send_instance_deploy_email", max_retries=1)
def send_instance_deploy_email(driverCls, provider, identity, instance_id,
        username, deploy_record_id):
    profile = UserProfile.objects.get(user__username=username)
    if not profile.send_emails:
        return
    core_instance = Instance.objects.get(provider_alias=instance_id)
    prior_successful_deploy = \
        DeployRecord.objects.filter(
                Q(instance=core_instance) &
                Q(status=DeployRecord.SUCCESS) &
                ~Q(id=deploy_record_id)).exists()
    if prior_successful_deploy:
        return
    driver = get_driver(driverCls, provider, identity)
    instance = driver.get_instance(instance_id)
    assert instance, "Instance no longer exists: {}".format(instance_id)
    created = datetime.strptime(instance.extra['created'],
                                "%Y-%m-%dT%H:%M:%SZ")
    send_instance_email(username,
                        instance.id,
                        instance.name,
                        instance.ip,
                        created,
                        username)


def _send_instance_email_with_failure(driverCls, provider, identity, instance_id, username, error_message):
    profile = UserProfile.objects.get(user__username=username)
    if not profile.send_emails:
        return
    driver = get_driver(driverCls, provider, identity)
    instance = driver.get_instance(instance_id)
    assert instance, "Instance no longer exists: {}".format(instance_id)
    created = datetime.strptime(instance.extra['created'],
                                "%Y-%m-%dT%H:%M:%SZ")
    send_instance_email(username,
                        instance.id,
                        instance.name,
                        instance.ip,
                        created,
                        username,
                        user_failure=True,
                        user_failure_message=error_message)


@task(name="fail_deploy_with_status")
def fail_deploy_with_status(request, exc, traceback, deploy_record_id, instance_alias, status):
    assert_active_record(deploy_record_id)
    try:
        instance = Instance.objects.get(provider_alias=instance_alias, end_date=None)
        InstanceStatusHistory.update_history(instance, status, "", extra=str(traceback))
    except Instance.DoesNotExist:
        pass
    mark_deploy_record_as_failure(deploy_record_id)

@task(name="error")
def error():
    raise Exception("OH NOO!")


@task(name="deploy_init_to")
def deploy_init_to(driverCls, provider, identity, instance_id, core_identity,
                   username=None, password=None, deploy=True,
                   *args, **kwargs):
    driver = get_driver(driverCls, provider, identity)
    instance = driver.get_instance(instance_id)
    assert instance, "Instance no longer exists: {}".format(instance_id)
    wait_active_task = wait_for_instance.si(instance.id, driverCls, provider, identity, "active")
    add_security_group = add_security_group_task.si(driverCls, provider, core_identity, instance.id)
    deploy_task = deploy.si(
        driverCls,
        provider,
        identity,
        instance_id,
        core_identity.uuid,
        username)
    has_secret = core_identity.get_credential('secret') is not None

    deploy_chain = wait_active_task
    if not has_secret:
        deploy_chain |= add_security_group
    deploy_chain |= deploy_task
    deploy_chain.delay()


@task(name="deploy")
def deploy(driverCls, provider, identity, instance_id, core_identity_uuid,
           username):
    """
    Calling deploy will replace any existing deploy with a new deploy and
    minimize duplicate code from running.

    Any deploy can be cancelled by end-dating its associated deploy record.
    """
    core_instance = Instance.objects.get(provider_alias=instance_id)
    deploy_record = None
    try:
        deploy_record = DeployRecord.create_record(core_instance)
    except IntegrityError:
        # In the case of two deploys racing to create a record defer here to
        # the instance that beat us
        return

    assert_current_deploy = assert_active_record.si(deploy_record.id)
    mark_deploy_failed = mark_deploy_record_as_failure.si(deploy_record.id)
    wait_for_active = assert_current_deploy | \
            wait_for_instance.si(instance_id, driverCls,
                                           provider, identity, "active",
                                           skip_final_status=True)
    start_networking = assert_current_deploy | \
        update_instance_status.si(instance_id, "networking", "initializing")
    fixed_ip_task = assert_current_deploy | add_fixed_ip.si(
        driverCls, provider, identity, instance_id, core_identity_uuid)
    floating_ip_task = assert_current_deploy | add_floating_ip.si(
        driverCls, provider, identity, core_identity_uuid, instance_id)
    check_reachability_task = assert_current_deploy | \
        update_instance_status.si(instance_id, "networking", "ensuring instance is reachable") | \
        check_reachability.si(instance_id)
    deploy_task = assert_current_deploy | \
        _deploy_instance.si(driverCls, provider, identity, instance_id, username, None)
    deploy_user_task = assert_current_deploy | \
        _deploy_instance_for_user.si(driverCls, provider, identity, instance_id, username)
    check_vnc_task = assert_current_deploy | \
        check_vnc.si(driverCls, provider, identity, instance_id, username)
    check_web_desktop = assert_current_deploy | check_web_desktop_task.si(
        driverCls, provider, identity, instance_id, username)
    deploy_failed_task = fail_deploy_with_status.s(deploy_record.id,
                                                   instance_id, "deploy_error")
    networking_failed_task = fail_deploy_with_status.s(
        deploy_record.id, instance_id, "networking_error")
    deploy_status_complete = assert_current_deploy | \
        update_instance_status.si(instance_id, "active", "") | \
        mark_deploy_record_as_success.si(deploy_record.id)
    deploy_email_task = send_instance_deploy_email.si(
        driverCls, provider, identity, instance_id, username, deploy_record.id)

    deploy_chain = wait_for_active
    deploy_chain |= start_networking
    deploy_chain |= fixed_ip_task
    deploy_chain |= floating_ip_task
    deploy_chain |= check_reachability_task
    deploy_chain.link_error(networking_failed_task)
    deploy_chain |= deploy_task
    deploy_chain |= check_web_desktop
    deploy_chain |= check_vnc_task
    deploy_chain |= deploy_user_task
    deploy_chain.link_error(deploy_failed_task)
    deploy_chain |= deploy_status_complete
    deploy_chain |= deploy_email_task

    return deploy_chain.delay()


@task(name="assert_active_record")
def assert_active_record(deploy_record_id):
    record = DeployRecord.objects.get(id=deploy_record_id)
    if not record.is_active():
        raise Exception("Deploy {} is no longer active (instance {})".format(record.id, record.instance.provider_alias))


@task(name="mark_deploy_record_as_success")
def mark_deploy_record_as_success(deploy_record_id):
    record = DeployRecord.objects.get(id=deploy_record_id)
    record.conclude_with_success()


@task(name="mark_deploy_record_as_failure")
def mark_deploy_record_as_failure(deploy_record_id):
    record = DeployRecord.objects.get(id=deploy_record_id)
    record.conclude_with_failure()


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


@task(name="check_reachability",
      soft_time_limit=60, # No retry can last longer than 1 minute
      max_retries=60,  # Attempt up to 30 minutes
      default_retry_delay=30,
      bind=True)
def check_reachability(self, instance_id):
    core_instance = Instance.objects.get(provider_alias=instance_id,
            end_date=None)
    username = core_instance.created_by.username
    try:
        ansible_ready_to_deploy(core_instance.ip_address, username, instance_id)
    except AnsibleDeployException as exc:
        self.retry(exc=exc)
    except (BaseException, Exception) as exc:
        celery_logger.exception(exc)
        self.retry(exc=exc)


@task(name="_deploy_instance_for_user",
      default_retry_delay=32,
      time_limit=32 * 60  # 32 minute hard-set time limit.
      )
def _deploy_instance_for_user(driverCls, provider, identity, instance_id, username,
                    **celery_task_args):
    celery_logger.debug("_deploy_instance_for_user task started at %s." % datetime.now())
    driver = get_driver(driverCls, provider, identity)
    instance = driver.get_instance(instance_id)
    assert instance, "Instance no longer exists: {}".format(instance_id)
    core_instance = Instance.objects.get(provider_alias=instance_id)
    InstanceStatusHistory.update_history(core_instance,
            "deploying", "running user services")
    first_deploy = not DeployRecord.has_deployed_successfully(core_instance)
    try:
        user_deploy(instance.ip, username, instance_id, first_deploy=first_deploy)
        celery_logger.debug("_deploy_instance_for_user task finished at %s." % datetime.now())
    except AnsibleDeployException as exc:
        celery_logger.exception(exc)
        _deploy_instance_for_user.retry(exc=exc)


@task(name="_deploy_instance",
      default_retry_delay=5,
      soft_time_limit=32 * 60,  # 32 minute hard-set time limit.
      max_retries=1
      # UNCOMMENT ME CONNOR
      )
def _deploy_instance(driverCls, provider, identity, instance_id,
                    username, password=None, token=None,
                    **celery_task_args):
    raise Exception("OH NOOOOO!!!")
    driver = get_driver(driverCls, provider, identity)
    instance = driver.get_instance(instance_id)
    assert instance, "Instance no longer exists: {}".format(instance_id)
    core_instance = Instance.objects.get(provider_alias=instance_id)
    InstanceStatusHistory.update_history(core_instance, "deploying", "initializing")
    try:
        instance_deploy(instance.ip, username, instance_id)
        celery_logger.debug("_deploy_instance task finished at %s." % datetime.now())
    except AnsibleDeployException as exc:
        celery_logger.exception(exc)
        _deploy_instance.retry(exc=exc)


@task(name="check_web_desktop_task", max_retries=2, default_retry_delay=15,
        bind=True)
def check_web_desktop_task(self, driverCls, provider, identity,
                       instance_alias, username, *args, **kwargs):
    driver = get_driver(driverCls, provider, identity)
    instance = driver.get_instance(instance_alias)
    assert instance, "Instance no longer exists: {}".format(instance_alias)
    celery_logger.debug("check_web_desktop_task started at %s." % datetime.now())
    core_instance = Instance.objects.get(provider_alias=instance_alias)
    InstanceStatusHistory.update_history(core_instance,
            "deploying", "checking support for NoVNC desktop")
    playbook_results = run_utility_playbooks(instance.ip, username,
            instance_alias, ["atmo_check_novnc.yml"],
            raise_exception=False)
    if execution_has_unreachable(playbook_results):
        try:
            self.retry()
        except MaxRetriesExceededError as exc:
            # After max attempts we mark the web desktop as disabled, the deploy
            # does not stop
            core_instance.web_desktop = False
            core_instance.save()
            return False
    desktop_enabled = not execution_has_failures(playbook_results)
    core_instance.web_desktop = desktop_enabled
    core_instance.save()
    return desktop_enabled


@task(name="check_vnc",
      max_retries=2,
      default_retry_delay=15,
      bind=True)
def check_vnc(self, driverCls, provider, identity,
                       instance_alias, username, *args, **kwargs):
    celery_logger.debug("check_vnc started at %s." % datetime.now())
    driver = get_driver(driverCls, provider, identity)
    instance = driver.get_instance(instance_alias)
    assert instance, "Instance no longer exists: {}".format(instance_alias)
    core_instance = Instance.objects.get(provider_alias=instance_alias)
    InstanceStatusHistory.update_history(core_instance,
            "deploying", "checking support for VNC desktop")
    playbook_results = run_utility_playbooks(instance.ip, username, instance_alias, ["atmo_check_vnc.yml"], raise_exception=False)
    if execution_has_unreachable(playbook_results):
        try:
            self.retry()
        except MaxRetriesExceededError as exc:
            # After max attempts we mark the vnc as disabled, the deploy
            # does not stop
            core_instance.vnc = False
            core_instance.save()
            return False

    vnc_enabled = not execution_has_failures(playbook_results)
    core_instance.vnc = vnc_enabled
    core_instance.save()
    return vnc_enabled


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


@task(name="deploy_status_error")
def deploy_status_error(request, exc, traceback, instance_alias, status):
    try:
        instance = Instance.objects.get(provider_alias=instance_alias, end_date=None)
        InstanceStatusHistory.update_history(instance, status, extra=str(traceback))
    except Instance.DoesNotExist:
        pass


@task(name="update_instance_status")
def update_instance_status(instance_alias, status, activity):
    instance = Instance.objects.get(provider_alias=instance_alias, end_date=None)
    InstanceStatusHistory.update_history(instance, status, activity)


@task(name="add_floating_ip",
      default_retry_delay=15,
      # UNCOMMENT ME CONNOR
      # max_retries=30,
      max_retries=1,
      bind=True)
def add_floating_ip(self, driverCls, provider, identity, core_identity_uuid,
                    instance_alias, *args, **kwargs):
    from service import instance as instance_service
    driver = get_driver(driverCls, provider, identity)
    instance = driver.get_instance(instance_alias)
    assert instance, "Instance no longer exists: {}".format(instance_alias)

    celery_logger.debug("add_floating_ip task started at %s." % datetime.now())
    core_identity = Identity.objects.get(uuid=core_identity_uuid)
    core_instance = Instance.objects.get(provider_alias=instance_alias)

    InstanceStatusHistory.update_history(core_instance, "networking", "adding floating ip")

    try:
        # Remove unused floating first
        driver._clean_floating_ip()
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
                admin_network_driver = instance_service._to_network_driver(admin_identity)
                routers = admin_network_driver.list_routers()
                public_router = None
                for router in routers:
                    if router['name'] == public_router_name:
                        public_router = router
                if not public_router:
                    raise Exception("Could not find a router matching"
                                    " public_router name {} for user {}"
                                    .format(public_router_name,
                                            core_identity.created_by.username))
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

        core_instance.ip_address = floating_ip_addr
        core_instance.save()
        return floating_ip
    except NeutronBadRequest:
        # This is an error on our end, we want it to surface
        raise
    except Exception as exc:
        celery_logger.exception("Error occurred while assigning a floating IP")
        self.retry(exc=exc)

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
