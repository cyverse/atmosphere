"""
Deploy methods for Atmosphere
"""
import os
import re

from django.template import Context
from django.template.loader import render_to_string
from django.utils.text import slugify
from django.utils.timezone import datetime

from libcloud.compute.deployment import ScriptDeployment

import subspace
from subspace.runner import Runner

from threepio import logger, deploy_logger

from atmosphere import settings
from atmosphere.settings import secrets

from django_cyverse_auth.protocol import ldap

from core.core_logging import create_instance_logger
from core.models.ssh_key import get_user_ssh_keys
from core.models import Provider, Identity

from service.exceptions import AnsibleDeployException


def ansible_deployment(
    instance_ip, username, instance_id, playbooks_dir,
    limit_playbooks=[], limit_hosts={}, extra_vars={},
    raise_exception=True):
    """
    Use service.ansible to deploy to an instance.
    """
    if not check_ansible():
        return []
    logger = create_instance_logger(
        deploy_logger,
        instance_ip,
        username,
        instance_id)
    hostname = build_host_name(instance_id, instance_ip)
    configure_ansible()
    if not limit_hosts:
        limit_hosts = {"hostname": hostname, "ip": instance_ip}
    host_file = settings.ANSIBLE_HOST_FILE
    identity = Identity.find_instance(instance_id)
    if identity:
        time_zone = identity.provider.timezone
        extra_vars.update({
            "TIMEZONE": time_zone,
        })
    extra_vars.update({
        "ATMOUSERNAME": username,
    })
    pbs = execute_playbooks(
        playbooks_dir, host_file, extra_vars, limit_hosts,
        logger=logger, limit_playbooks=limit_playbooks)
    if raise_exception:
        raise_playbook_errors(pbs, instance_ip, hostname)
    return pbs


def ready_to_deploy(instance_ip, username, instance_id):
    """
    Use service.ansible to deploy to an instance.
    """
    playbooks_dir = settings.ANSIBLE_PLAYBOOKS_DIR
    playbooks_dir = os.path.join(playbooks_dir, 'utils')

    return ansible_deployment(
        instance_ip, username, instance_id, playbooks_dir,
        limit_playbooks=['check_networking.yml'])


def instance_deploy(instance_ip, username, instance_id,
		    limit_playbooks=[]):
    """
    Use service.ansible to deploy to an instance.
    """
    extra_vars = {
        "VNCLICENSE": secrets.ATMOSPHERE_VNC_LICENSE,
    }
    playbooks_dir = settings.ANSIBLE_PLAYBOOKS_DIR
    playbooks_dir = os.path.join(playbooks_dir, 'instance_deploy')

    return ansible_deployment(
        instance_ip, username, instance_id, playbooks_dir,
        limit_playbooks=limit_playbooks,
        extra_vars=extra_vars)


def user_deploy(instance_ip, username, instance_id):
    """
    Use service.ansible to deploy to an instance.
    """
    playbooks_dir = settings.ANSIBLE_PLAYBOOKS_DIR
    playbooks_dir = os.path.join(playbooks_dir, 'user_deploy')
    user_keys = [k.pub_key for k in get_user_ssh_keys(username)]
    extra_vars = {
        "USERSSHKEYS": user_keys
    }
    return ansible_deployment(
        instance_ip, username, instance_id, playbooks_dir,
        extra_vars=extra_vars)


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
        instance_ip, username, instance_id, playbooks_dir, limit_playbooks,
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


def execute_playbooks(playbook_dir, host_file, extra_vars, my_limit,
                      logger=None, limit_playbooks=None,
                      runner_strategy='all', **runner_opts):
    # Force requirement of a logger for 2.0 playbook runs
    if not logger:
        logger = deploy_logger
    if runner_strategy == 'single':
        return _one_runner_one_playbook_execution(
            playbook_dir, host_file, extra_vars, my_limit,
            logger=logger, limit_playbooks=limit_playbooks, **runner_opts)
    else:
        return _one_runner_all_playbook_execution(
            playbook_dir, host_file, extra_vars, my_limit,
            logger=logger, limit_playbooks=limit_playbooks, **runner_opts)


def _one_runner_all_playbook_execution(
        playbook_dir, host_file, extra_vars, my_limit,
        logger=None, limit_playbooks=None, **runner_opts):
    runner = Runner.factory(
            host_file,
            playbook_dir,
            run_data=extra_vars,
            limit_hosts=my_limit,
            logger=logger,
            limit_playbooks=limit_playbooks,
            # Use atmosphere settings
            group_vars_map={
                filename: os.path.join(
                    settings.ANSIBLE_GROUP_VARS_DIR, filename)
                for filename in os.listdir(settings.ANSIBLE_GROUP_VARS_DIR)},
            private_key_file=settings.ATMOSPHERE_PRIVATE_KEYFILE,
            **runner_opts)
    if runner.playbooks == []:
        msg = "Playbook directory has no playbooks: %s" \
            % (playbook_dir, )
        if limit_playbooks:
            msg = "'limit_playbooks=%s' generated zero playbooks." \
                  " Available playbooks in directory are: %s" \
                  % (limit_playbooks, runner._get_files(playbook_dir))
        raise AnsibleDeployException(msg)
    runner.run()
    return runner


def _one_runner_one_playbook_execution(
        playbook_dir, host_file, extra_vars, my_limit,
        logger=None, limit_playbooks=None, **runner_opts):
    runners = [Runner.factory(
            host_file,
            os.path.join(playbook_dir, playbook_path),
            run_data=extra_vars,
            limit_hosts=my_limit,
            logger=logger,
            limit_playbooks=limit_playbooks,
            # Use atmosphere settings
            group_vars_map={
                filename: os.path.join(
                    settings.ANSIBLE_GROUP_VARS_DIR, filename)
                for filename in os.listdir(settings.ANSIBLE_GROUP_VARS_DIR)},
            private_key_file=settings.ATMOSPHERE_PRIVATE_KEYFILE,
            **runner_opts)
        for playbook_path in os.listdir(playbook_dir)
        if not limit_playbooks or playbook_path in limit_playbooks]
    [runner.run() for runner in runners]
    return runners


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


def configure_ansible():
    """
    Configure ansible to work with service.ansible and subspace.
    """
    subspace.set_constants("HOST_KEY_CHECKING", False)
    subspace.set_constants(
        "DEFAULT_ROLES_PATH", settings.ANSIBLE_ROLES_PATH)
    if settings.ANSIBLE_CONFIG_FILE:
        os.environ["ANSIBLE_CONFIG"] = settings.ANSIBLE_CONFIG_FILE
        os.environ["PYTHONOPTIMIZE"] = "1" #NOTE: Required to run ansible2 + celery + prefork concurrency
        #os.environ["ANSIBLE_DEBUG"] = "true"
        # Alternatively set this in ansible.cfg: debug = true
        subspace.constants.reload_config()


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
                "(ex:'vm%(three)s-%(four)s.my_domain.com')"
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


def playbook_error_message(runner_details, error_name):
    return ("%s with PlayBook(s) => %s|"
            % (
               error_name,
               runner_details
              ))


def execution_has_unreachable(pbs, hostname):
    if type(pbs) != list:
        pbs = [pbs]
    return any(pb.stats.dark for pb in pbs)


def execution_has_failures(pbs, hostname):
    if type(pbs) != list:
        pbs = [pbs]
    return any(pb.stats.failures for pb in pbs)


def raise_playbook_errors(pbs, instance_ip, hostname, allow_failures=False):
    """
    """
    if not type(pbs) == list:
        pbs = [pbs]
    error_message = ""
    for pb in pbs:
        if pb.stats.dark:
            if hostname in pb.stats.dark:
                error_message += playbook_error_message(
                    pb.stats.dark[hostname], "Unreachable")
            elif instance_ip in pb.stats.dark:
                error_message += playbook_error_message(
                    pb.stats.dark[instance_ip], "Unreachable")
        if not allow_failures and pb.stats.failures:
            if hostname in pb.stats.failures:
                error_message += playbook_error_message(
                    pb.stats.failures[hostname], "Failures")
            elif instance_ip in pb.stats.failures:
                error_message += playbook_error_message(
                    pb.stats.failures[instance_ip], "Failures")
    if error_message:
        msg = error_message[:-2] + str(pb.stats.processed_playbooks.get(hostname,{}))
        raise AnsibleDeployException(msg)


def sync_instance():
    return ScriptDeployment("sync", name="./deploy_sync_instance.sh")


def deploy_test():
    return ScriptDeployment(
        "\n", name="./deploy_test.sh")


def freeze_instance(sleep_time=45):
    return ScriptDeployment(
        "nohup fsfreeze -f / && sleep %s && fsfreeze -u / &" % sleep_time,
        name="./deploy_freeze_instance.sh")


def mount_volume(device, mount_location, username=None, group=None):
    mount_script = "mkdir -p %s; " % (mount_location,)
    mount_script += "mount %s %s; " % (device, mount_location)
    if username and group:
        mount_script += "chown -R %s:%s %s" % (username, group, mount_location)
    # NOTE: Fails to recognize mount_script as a str
    # Removing this line will cause 'celery' to fail
    # to execute this particular ScriptDeployment
    return ScriptDeployment(str(mount_script), name="./deploy_mount_volume.sh")


def check_mount():
    return ScriptDeployment("mount",
                            name="./deploy_check_mount.sh")


def check_process(proc_name):
    return ScriptDeployment(
        "if ps aux | grep '%s' > /dev/null; "
        "then echo '1:%s is running'; "
        "else echo '0:%s is NOT running'; "
        "fi"
        % (proc_name, proc_name, proc_name),
        name="./deploy_check_process_%s.sh"
        % (proc_name,))


def check_volume(device):
    return ScriptDeployment("tune2fs -l %s" % (device),
                            name="./deploy_check_volume.sh")


def mkfs_volume(device):
    return ScriptDeployment("mkfs.ext3 -F %s" % (device),
                            name="./deploy_mkfs_volume.sh")


def umount_volume(mount_location):
    return ScriptDeployment("mounts=`mount | grep '%s' | cut -d' ' -f3`; "
                            "for mount in $mounts; do umount %s; done;"
                            % (mount_location, mount_location),
                            name="./deploy_umount_volume.sh")


def lsof_location(mount_location):
    return ScriptDeployment("lsof | grep %s" % (mount_location),
                            name="./deploy_lsof_location.sh")


def step_script(step):
    script = str(step.script)
    if not script.startswith("#!"):
        script = "#! /usr/bin/env bash\n" + script
    return ScriptDeployment(script, name="./" + step.get_script_name())

def shell_lookup_helper(username):
    zsh_user = False
    ldap_info = ldap._search_ldap(username)
    try:
        ldap_info_dict = ldap_info[0][1]
    except IndexError:
        return False
    for key in ldap_info_dict.iterkeys():
        if key == "loginShell":
            if 'zsh' in ldap_info_dict[key][0]:
                zsh_user = True
    return zsh_user


def echo_test_script():
    return ScriptDeployment(
        'echo "Test deployment working @ %s"' % datetime.now(),
        name="./deploy_echo.sh")


def wrap_script(script_text, script_name):
    """
    NOTE: In current implementation, the script can only be executed, and not
    logged.

    Implementation v2:
    * Write to file
    * Chmod the file
    * Execute and redirect output to stdout/stderr to logfile.
    """
    # logfile = "/var/log/atmo/post_boot_scripts.log"
    # kludge: weirdness without the str cast...
    script_text = str(script_text)
    full_script_name = "./deploy_boot_script_%s.sh" % (slugify(script_name),)
    return ScriptDeployment(
        script_text, name=full_script_name)


def inject_env_script(username):
    """
    This is the 'raw script' that will be used to prepare the environment.
    TODO: Find a better home for this. Probably use ansible for this.
    """
    env_file = "$HOME/.bashrc"
    template = "scripts/bash_inject_env.sh"
    context = {
        "username": username,
        "env_file": env_file,
    }
    rendered_script = render_to_string(
        template, context=Context(context))
    return rendered_script