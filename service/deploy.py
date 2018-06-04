"""
Deploy methods for Atmosphere
"""
import os
import re
import json

from django.template.loader import render_to_string
from django.utils.text import slugify
from django.utils.timezone import datetime


from ansible.cli.playbook import PlaybookCLI

from threepio import logger, deploy_logger

from atmosphere import settings
from atmosphere.settings import secrets

from django_cyverse_auth.protocol import ldap

from core.core_logging import create_instance_logger
from core.models.ssh_key import get_user_ssh_keys
from core.models import Provider, Identity, Instance, SSHKey, AtmosphereUser

from service.exceptions import (
    AnsibleDeployException, DeviceBusyException, NonZeroDeploymentException
)


def ansible_deployment(
    instance_ip, username, instance_id, playbooks_dir,
    limit_playbooks=[], limit_hosts={}, extra_vars={},
    raise_exception=True, debug=False):
    """
    Use service.ansible to deploy to an instance.
    """
    if not check_ansible():
        return []
    # Expecting to be path-relative to the playbook path, so use basename
    if type(limit_playbooks) == str:
        limit_playbooks = limit_playbooks.split(",")
    if type(limit_playbooks) != list:
        raise Exception("Invalid 'limit_playbooks' argument (%s). Expected List" % limit_playbooks)
    if limit_playbooks == []:
        limit_playbooks = sorted(os.listdir(playbooks_dir))
    logger = create_instance_logger(
        deploy_logger,
        instance_ip,
        username,
        instance_id)
    hostname = build_host_name(instance_id, instance_ip)
    configure_ansible(debug=debug)
    if not limit_hosts:
        if hostname:
            limit_hosts = hostname
        else:
            limit_hosts = instance_ip
    host_file = settings.ANSIBLE_HOST_FILE
    identity = Identity.find_instance(instance_id)
    if identity:
        time_zone = identity.provider.timezone
        extra_vars.update({
            "TIMEZONE": time_zone,
        })
    shared_users = list(AtmosphereUser.users_for_instance(instance_id).values_list('username', flat=True))
    if not shared_users:
        shared_users = [username]
    if username not in shared_users:
        shared_users.append(username)
    extra_vars.update({
        "SHARED_USERS": shared_users,
    })
    extra_vars.update({
        "ATMOUSERNAME": username,
    })
    extra_vars.update({
        "INSTANCE_UUID": instance_id,
    })
    playbook_results = execute_playbooks(
        playbooks_dir, host_file, extra_vars, limit_hosts,
        logger=logger, limit_playbooks=limit_playbooks)
    if raise_exception:
        raise_playbook_errors(playbook_results, instance_id, instance_ip, hostname)
    return playbook_results


def ready_to_deploy(instance_ip, username, instance_id):
    """
    Use service.ansible to deploy to an instance.
    """
    playbooks_dir = settings.ANSIBLE_PLAYBOOKS_DIR
    playbooks_dir = os.path.join(playbooks_dir, 'utils')
    extra_vars = {
        "SSH_IDENTITY_FILE": settings.ATMOSPHERE_PRIVATE_KEYFILE,
    }

    return ansible_deployment(
        instance_ip, username, instance_id, playbooks_dir,
        limit_playbooks=['check_networking.yml'],
        extra_vars=extra_vars)


def deploy_mount_volume(instance_ip, username, instance_id,
        device, mount_location=None, device_type='ext4'):
    """
    Use service.ansible to mount volume to an instance.
    """
    extra_vars = {
        "VOLUME_DEVICE": device,
        "VOLUME_MOUNT_LOCATION": mount_location,
        "VOLUME_DEVICE_TYPE": device_type,
    }
    playbooks_dir = settings.ANSIBLE_PLAYBOOKS_DIR
    playbooks_dir = os.path.join(playbooks_dir, 'instance_actions')
    limit_playbooks = ['mount_volume.yml']
    return ansible_deployment(
        instance_ip, username, instance_id, playbooks_dir,
        limit_playbooks=limit_playbooks,
        extra_vars=extra_vars)


def deploy_unmount_volume(instance_ip, username, instance_id,
        device):
    """
    Use service.ansible to mount volume to an instance.
    """
    extra_vars = {
        "src": device
    }
    playbooks_dir = settings.ANSIBLE_PLAYBOOKS_DIR
    playbooks_dir = os.path.join(playbooks_dir, 'instance_actions')
    limit_playbooks = ['unmount_volume.yml']
    playbook_results = ansible_deployment(
        instance_ip, username, instance_id, playbooks_dir,
        limit_playbooks=limit_playbooks,
        extra_vars=extra_vars,
        raise_exception=False)
    return playbook_results


def _raise_lsof_playbook_failure(device, lsof_rc, lsof_stdout):
    """
    - Scrape the stdout from 'lsof' call
    - Collect a list of pids currently in use
    - raise a DeviceBusyException
    """
    regex = re.compile("(?P<name>[\w]+)\s*(?P<pid>[\d]+)")
    offending_processes = []
    for line in lsof_stdout.split('\n'):
        match = regex.search(line)
        if not match:
            continue
        search_dict = match.groupdict()
        offending_processes.append(
            (search_dict['name'], search_dict['pid'])
        )
    raise DeviceBusyException(device, offending_processes)


def deploy_prepare_snapshot(instance_ip, username, instance_id, extra_vars={}):
    playbooks_dir = settings.ANSIBLE_PLAYBOOKS_DIR
    playbooks_dir = os.path.join(playbooks_dir, 'imaging')
    limit_playbooks = ['prepare_instance_snapshot.yml']
    return ansible_deployment(
        instance_ip, username, instance_id, playbooks_dir,
        limit_playbooks=limit_playbooks,
        extra_vars=extra_vars)


def deploy_check_volume(instance_ip, username, instance_id,
        device, device_type='ext4'):
    """
    Use ansible to check if an attached volume has run mkfs.
    """
    extra_vars = {
        "VOLUME_DEVICE": device,
        "VOLUME_DEVICE_TYPE": device_type,
    }
    playbooks_dir = settings.ANSIBLE_PLAYBOOKS_DIR
    playbooks_dir = os.path.join(playbooks_dir, 'instance_actions')
    limit_playbooks = ['check_volume.yml']
    return ansible_deployment(
        instance_ip, username, instance_id, playbooks_dir,
        limit_playbooks=limit_playbooks,
        extra_vars=extra_vars)


def instance_deploy(instance_ip,
                    username,
                    instance_id,
                    limit_playbooks=[]):
    """
    Use service.ansible to deploy to an instance.
    """

    extra_vars = {
        "SSH_IDENTITY_FILE": settings.ATMOSPHERE_PRIVATE_KEYFILE,
        "VNCLICENSE": secrets.ATMOSPHERE_VNC_LICENSE,
    }
    playbooks_dir = settings.ANSIBLE_PLAYBOOKS_DIR
    playbooks_dir = os.path.join(playbooks_dir, 'instance_deploy')

    return ansible_deployment(
        instance_ip, username, instance_id, playbooks_dir,
        limit_playbooks=limit_playbooks,
        extra_vars=extra_vars)


def user_deploy(instance_ip, username, instance_id, first_deploy=True):
    """
    Use service.ansible to deploy to an instance.
    #NOTE: This method will _NOT_ work if you do not run instance deployment *FIRST*!
    # In order to add user-ssh keys to root, you will need root access to the VM that is *not* configured in this playbook.
    """
    playbooks_dir = settings.ANSIBLE_PLAYBOOKS_DIR
    playbooks_dir = os.path.join(playbooks_dir, 'user_deploy')

    #TODO: 'User-selectable 'SSH strategy' for instances?
    # Example 'user only' strategy:
    # user_keys = [k.pub_key for k in get_user_ssh_keys(username)]
    instance = Instance.objects.get(provider_alias=instance_id)
    image_scripts = instance.source.providermachine.application_version.boot_scripts.all()
    instance_scripts = instance.scripts.all()
    scripts = image_scripts.union(instance_scripts)

    # Example 'all members'  strategy:
    if not instance.project:
        raise Exception("Expected this instance to have a project, found None: %s" % instance)
    group = instance.project.owner
    group_ssh_keys = SSHKey.keys_for_group(group)
    user_keys = [k.pub_key for k in group_ssh_keys]

    async_scripts, deploy_scripts = [], []
    for script in scripts:
        if not (first_deploy or script.run_every_deploy):
            continue
        if script.wait_for_deploy:
            deploy_scripts.append(script)
        else:
            async_scripts.append(script)

    format_script = lambda s: {"name": s.get_title_slug(), "text": s.get_text()}
    extra_vars = {
        "USERSSHKEYS": user_keys,
        "ASYNC_SCRIPTS":  map(format_script, async_scripts),
        "DEPLOY_SCRIPTS":  map(format_script, deploy_scripts)
    }
    playbook_results = ansible_deployment(
        instance_ip, username, instance_id, playbooks_dir,
        extra_vars=extra_vars, raise_exception=False)
    hostname = build_host_name(instance_id, instance_ip)
    # An error has occurred during deployment!
    # If the failure was not related to users boot-scripts,
    # handle as a generic ansible failure.
    return raise_playbook_errors(playbook_results, instance_id, instance_ip, hostname)


def run_utility_playbooks(instance_ip, username, instance_id,
                          limit_playbooks=[], raise_exception=True):
    """
    Use service.ansible to deploy utility_playbooks to an instance.
    'limit_playbooks' is a list of strings
    that should match the filename you wish to include
    (Ex: check_networking.yml)
    """
    playbooks_dir = os.path.join(settings.ANSIBLE_PLAYBOOKS_DIR, 'utils')
    return ansible_deployment(
        instance_ip,
        username,
        instance_id,
        playbooks_dir,
        limit_playbooks,
        raise_exception=raise_exception)


def select_install_playbooks(install_action):
    """
    This function would take an install_action, say:
    `apache` or `nginx` or `R` or `Docker`
    and return as a result, the list of playbooks required to make it happen.
    """
    raise Exception("Unknown installation action:%s" % install_action)


def user_deploy_install(instance_ip, username, instance_id, install_action, install_args):
    """
    Placeholder function to show how a user-initialized install from Troposphere might be handled on the backend.
    """
    playbooks_dir = settings.ANSIBLE_PLAYBOOKS_DIR
    playbooks_dir = os.path.join(playbooks_dir, 'user_customizations')
    limit_playbooks = select_install_playbooks(install_action)
    return ansible_deployment(
        instance_ip, username, instance_id, playbooks_dir,
        limit_playbooks, extra_vars=install_args)


def execute_playbooks(playbook_dir, host_file, extra_vars, host,
                      logger=None, limit_playbooks=[]):
    # Force requirement of a logger for 2.0 playbook runs
    if not logger:
        logger = deploy_logger

    inventory_dir = "%s/ansible" % settings.ANSIBLE_ROOT

    # Run playbooks
    results = []
    for pb in limit_playbooks:
        logger.info("Executing playbook %s/%s" % (playbook_dir, pb))
        args = [
            "--inventory-file=%s" % inventory_dir,
            "--limit=%s" % host,
            "--extra-vars=%s" % json.dumps(extra_vars),
            "%s/%s" % (playbook_dir, pb)
        ]
        pb_runner = PlaybookCLI(args)
        pb_runner.parse()
        results.append(pb_runner.run())
        if results[-1] != 0: break
    return results


def check_ansible():
    """
    If the playbooks and roles directory exist then ANSIBLE_* settings
    variables are likely configured.
    """
    exists = os.path.exists(settings.ANSIBLE_PLAYBOOKS_DIR) and\
        os.path.exists(settings.ANSIBLE_ROLES_PATH)
    if not exists:
        logger.warn("Ansible is not configured. Verify your "
                    "ANSIBLE_* settings variables")
    return exists


def configure_ansible(debug=False):
    """
    Configure ansible to work with service.ansible and subspace.
    """

    os.environ["ANSIBLE_DEBUG"] = "true" if debug else "false"
    if settings.ANSIBLE_CONFIG_FILE:
        os.environ["ANSIBLE_CONFIG"] = settings.ANSIBLE_CONFIG_FILE
        os.environ["PYTHONOPTIMIZE"] = "1" #NOTE: Required to run ansible2 + celery + prefork concurrency


def build_host_name(instance_id, ip):
    """
    Build host name from the configuration in settings
    See:
    * INSTANCE_HOSTNAMING_FORMAT
    * INSTANCE_HOSTNAMING_DOMAIN (Required if you use `%(domain)s`)
    """
    try:
        provider = Provider.objects.get(instancesource__instances__provider_alias=instance_id)
        hostname_format_str = provider.cloud_config['deploy']['hostname_format']
    except Provider.DoesNotExist:
        logger.warn("Using an instance %s that is *NOT* in your database. Cannot determine hostnaming format. Using IP address as hostname.")
        return raw_hostname(ip)
    except (KeyError, TypeError):
        logger.warn("Cloud config ['deploy']['hostname_format'] is missing -- using IP address as a hostname.")
        return raw_hostname(ip)

    # Convert IP into a dictionary broken into octets
    hostnaming_format_map = create_hostnaming_map(ip)
    try:
        if all((str_val not in hostname_format_str) for str_val
                in ['one', 'two', 'three', 'four']):
            raise ValueError(
                "Invalid HOSTNAME_FORMAT: Expected string containing "
                "at least one of the IP octets. Received: %s"
                "(ex:'vm%%(three)s-%%(four)s.my_domain.com')"
                % hostname_format_str)
        return hostname_format_str % hostnaming_format_map
    except (KeyError, TypeError, ValueError):
        logger.exception("Invalid instance_hostname_format: %s" % hostname_format_str)
        return raw_hostname(ip)


def create_hostnaming_map(ip):
    try:
        regex = re.compile(
            "(?P<one>[0-9]+)\.(?P<two>[0-9]+)\."
            "(?P<three>[0-9]+)\.(?P<four>[0-9]+)")
        r = regex.search(ip)
        (one, two, three, four) = r.groups()
        domain = getattr(settings, 'INSTANCE_HOSTNAMING_DOMAIN', None)
        hostname_map = {
            'one': one,
            'two': two,
            'three': three,
            'four': four,
            'domain': domain
            }
        return hostname_map
    except Exception:
        raise Exception(
            "IPv4 Address expected: <%s> is not of the format VVV.XXX.YYY.ZZZ"
            % ip)


def raw_hostname(ip):
    """
    For now, return raw IP
    """
    return ip


def get_playbook_filename(filename):
    rel = os.path.relpath(os.path.dirname(filename),
                          settings.ANSIBLE_PLAYBOOKS_DIR)
    basename = os.path.basename(filename)
    if rel != ".":
        return os.path.join(rel, basename)
    else:
        return basename


def execution_has_unreachable(playbook_results):
    """Return value 4 means unreachable in ansible-playbook"""
    if type(playbook_results) != list:
        playbook_results = [playbook_results]
    return 4 in playbook_results


def execution_has_failures(playbook_results):
    """Return value 2 means failure in ansible-playbook"""
    if type(playbook_results) != list:
        playbook_results = [playbook_results]
    return 2 in playbook_results


def raise_playbook_errors(playbook_results, instance_id, instance_ip, hostname, allow_failures=False):
    """
    Return value 4 means unreachable/dark
    Return value 2 means failure
    """
    if not type(playbook_results) == list:
        playbook_results = [playbook_results]
    error_message = ""
    for rc in playbook_results:
        if rc == 4:
            error_message += "Unreachable"
        elif not allow_failures and rc == 2:
            error_message += "Failed"
    if error_message:
        msg = "Instance: %s IP:%s %s - %s" % (
            instance_id,
            instance_ip,
            'Hostname: ' + hostname if hostname else "",
            error_message
        )
        raise AnsibleDeployException(msg)
