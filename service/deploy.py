"""
Deploy methods for Atmosphere
"""
from functools import wraps
import os
import sys
import time

from django.utils.timezone import datetime

from libcloud.compute.deployment import Deployment, ScriptDeployment,\
    MultiStepDeployment

import redis

import subspace

from threepio import logger, logging, deploy_logger

from atmosphere import settings
from atmosphere.settings import secrets

from authentication.protocol import ldap

from core.logging import create_instance_logger

from service.exceptions import AnsibleDeployException


r = None


def create_redis_client():
    global r
    r = redis.StrictRedis()


create_redis_client()


class WriteFileDeployment(Deployment):
    def __init__(self, full_text, target):
        """
        :type target: ``str``
        :keyword target: Path to install file on node

        :type full_text: ``str``
        :keyword full_text: Text to install file on node
        """
        self.full_text = full_text
        self.target = target

    def run(self, node, client):
        client.put(self.target,  contents=self.full_text, mode='w')
        return node


class LoggedScriptDeployment(ScriptDeployment):
    def __init__(self, script, name=None, delete=False, logfile=None,
                 attempts=1):
        """
        Use this for client-side logging
        """
        super(LoggedScriptDeployment, self).__init__(
            script, name=name, delete=delete)
        self.attempts = attempts
        if logfile:
            self.script = self.script + " >> %s 2>&1" % logfile
        #logger.info(self.script)

    def run(self, node, client):
        """
        Server-side logging

        Optional Param: attempts - # of times to retry
        in the event of a Non-Zero exit status(code)
        """
        attempt = 0
        retry_time = 0
        while attempt < self.attempts:
            node = super(LoggedScriptDeployment, self).run(node, client)
            if self.exit_status == 0:
                break
            attempt += 1
            retry_time = 2 * 2**attempt  # 4,8,16..
            logger.debug(
                "WARN: Script %s on Node %s is non-zero."
                " Will re-try in %s seconds. Attempt: %s/%s"
                % (node.id, self.name, retry_time, attempt, self.attempts))
            time.sleep(retry_time)

        if self.stdout:
            logger.debug('%s (%s)STDOUT: %s' % (node.id, self.name,
                                                self.stdout))
        if self.stderr:
            logger.warn('%s (%s)STDERR: %s' % (node.id, self.name,
                                               self.stderr))
        return node


def deploy_to(instance_ip, username, instance_id):
    """
    Use service.ansible to deploy to an instance.
    """
    if not check_ansible():
        return []
    logger = create_instance_logger(deploy_logger, instance_ip, username, instance_id)
    hostname = build_host_name(instance_ip)
    cache_bust_redis(hostname)
    configure_ansible(logger)
    my_limit = {"hostname": hostname, "ip": instance_ip}
    deploy_playbooks = settings.ANSIBLE_PLAYBOOKS_DIR
    host_list = settings.ANSIBLE_HOST_FILE
    extra_vars = {"ATMOUSERNAME" : username,
                  "VNCLICENSE" : secrets.ATMOSPHERE_VNC_LICENSE}
    pbs = subspace.playbook.get_playbooks(deploy_playbooks,
                                          host_list=host_list,
                                          limit=my_limit,
                                          extra_vars=extra_vars)
    [pb.run() for pb in pbs]
    log_playbook_summaries(logger, pbs, hostname)
    raise_playbook_errors(pbs, hostname)
    return pbs


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


def configure_ansible(logger):
    """
    Configure ansible to work with service.ansible and subspace.
    """
    subspace.constants("HOST_KEY_CHECKING", False)
    subspace.constants("DEFAULT_ROLES_PATH",
                       settings.ANSIBLE_ROLES_PATH)
    if settings.ANSIBLE_CONFIG_FILE:
        subspace.constants("ANSIBLE_CONFIG",
                           settings.ANSIBLE_CONFIG_FILE)
    subspace.use_logger(logger)


def build_host_name(ip):
    list_of_subnet = ip.split(".")
    return "vm%s-%s" % (list_of_subnet[2], list_of_subnet[3])


def cache_bust_redis(hostname):
    r.del("ansible_facts%s" % hostname)


def log_playbook_summaries(logger, pbs, hostname):
    summaries = [(pb.filename, pb.stats.summarize(hostname)) for pb in pbs]
    for filename, summary in summaries:
        logger.info(get_playbook_filename(filename) + str(summary))


def get_playbook_filename(filename):
    rel = os.path.relpath(os.path.dirname(filename),
                          settings.ANSIBLE_PLAYBOOKS_DIR)
    basename = os.path.basename(filename)
    if rel != ".":
        return os.path.join(rel, basename)
    else:
        return basename


def playbook_error_message(count, error_name, pb):
    return ("%s => %s with PlayBook %s|"
            % (count, error_name, get_playbook_filename(pb.filename)))


def raise_playbook_errors(pbs, hostname):
    error_message = ""
    for pb in pbs:
        if pb.stats.dark:
            error_message += playbook_error_message(
                pb.stats.dark[hostname], "Unreachable", pb)
        if pb.stats.failures:
            error_message += playbook_error_message(
                pb.stats.failures[hostname], "Failures", pb)
    if error_message:
        raise AnsibleDeployException(error_message[:-1])


def sync_instance():
    return ScriptDeployment("sync", name="./deploy_sync_instance.sh")


def get_distro(distro='ubuntu'):
    return ScriptDeployment("cat /etc/*-release",
                            name="./deploy_get_distro.sh")


def build_script(script_input, name=None):
    return ScriptDeployment(script_input, name=name)


def deploy_test():
    return ScriptDeployment(
        "\n", name="./deploy_test.sh")


def install_base_requirements(distro='ubuntu'):
    script_txt = "%s install -qy utils-linux %s"\
        % ('apt-get' if 'ubuntu' in distro.to_lower() else 'yum',
           '' if 'ubuntu' in distro.to_lower() else 'python-simplejson')
    return ScriptDeployment(script_txt,
                            name="./deploy_base_requirements.sh")


def freeze_instance(sleep_time=45):
    return ScriptDeployment(
        "nohup fsfreeze -f / && sleep %s && fsfreeze -u / &" % sleep_time,
        name="./deploy_freeze_instance.sh")


def mount_volume(device, mount_location, username=None, group=None):
    mount_script = "mkdir -p %s; " % (mount_location,)
    mount_script += "mount %s %s; " % (device, mount_location)
    if username and group:
        mount_script += "chown -R %s:%s %s" % (username, group, mount_location)
    #NOTE: Fails to recognize mount_script as a str
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
    return ScriptDeployment("mkfs.ext3 %s" % (device),
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


def wget_file(filename, url, logfile=None, attempts=3):
    name = './deploy_wget_%s.sh' % (os.path.basename(filename))
    return LoggedScriptDeployment(
        "wget -O %s %s" % (filename, url),
        name=name, attempts=attempts, logfile=logfile)


def chmod_ax_file(filename, logfile=None):
    return LoggedScriptDeployment(
        "chmod a+x %s" % filename,
        name='./deploy_chmod_ax.sh',
        logfile=logfile)


def package_deps(logfile=None, username=None):
    #These requirements are for Editors, Shell-in-a-box, etc.
    do_ubuntu = "apt-get update;apt-get install -y emacs vim wget "\
                + "language-pack-en make gcc g++ gettext texinfo "\
                + "autoconf automake python-httplib2 "
    do_centos = "yum install -y emacs vim-enhanced wget make "\
                + "gcc gettext texinfo autoconf automake "\
                + "python-simplejson python-httplib2 "
    if shell_lookup_helper(username):
        do_ubuntu = do_ubuntu + "zsh "
        do_centos = do_centos + "zsh "
    return LoggedScriptDeployment(
        "distro_cat=`cat /etc/*-release`\n"
        + "if [[ $distro_cat == *Ubuntu* ]]; then\n"
        + do_ubuntu
        + "\nelse if [[ $distro_cat == *CentOS* ]];then\n"
        + do_centos
        + "\nfi\nfi",
        name="./deploy_package_deps.sh",
        logfile=logfile)


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


def redeploy_script(filename, username, instance, logfile=None):
    awesome_atmo_call = "%s --service_type=%s --service_url=%s"
    awesome_atmo_call += " --server=%s --user_id=%s"
    awesome_atmo_call += " --redeploy"
    awesome_atmo_call %= (
        filename,
        "instance_service_v1",
        settings.INSTANCE_SERVICE_URL,
        settings.DEPLOY_SERVER_URL,
        username)
    #kludge: weirdness without the str cast...
    str_awesome_atmo_call = str(awesome_atmo_call)
    #logger.debug(isinstance(str_awesome_atmo_call, basestring))
    return LoggedScriptDeployment(
        str_awesome_atmo_call,
        name='./deploy_call_atmoinit.sh',
        logfile=logfile)


def init_script(filename, username, token, instance, password,
                redeploy, logfile=None):
    awesome_atmo_call = "%s --service_type=%s --service_url=%s"
    awesome_atmo_call += " --server=%s --user_id=%s"
    awesome_atmo_call += " --token=%s --name=\"%s\""
    awesome_atmo_call += "%s"
    awesome_atmo_call += " --vnc_license=%s"
    awesome_atmo_call %= (
        filename,
        "instance_service_v1",
        settings.INSTANCE_SERVICE_URL,
        settings.DEPLOY_SERVER_URL,
        username,
        token,
        instance.name.replace('"', '\\\"'),  # Prevents single " from preventing calls to atmo_init_full
        " --redeploy" if redeploy else "",
        secrets.ATMOSPHERE_VNC_LICENSE)
    if password:
        awesome_atmo_call += " --root_password=%s" % (password)
    #kludge: weirdness without the str cast...
    str_awesome_atmo_call = str(awesome_atmo_call)
    #logger.debug(isinstance(str_awesome_atmo_call, basestring))
    return LoggedScriptDeployment(
        str_awesome_atmo_call,
        name='./deploy_call_atmoinit.sh',
        logfile=logfile)


def rm_scripts(logfile=None):
    return LoggedScriptDeployment(
        "rm -rf ~/deploy_*",
        name='./deploy_remove_scripts.sh',
        logfile=logfile)


def echo_test_script():
    return ScriptDeployment(
        'echo "Test deployment working @ %s"' % datetime.now(),
        name="./deploy_echo.sh")


def init_log():
    return ScriptDeployment(
        'if [ ! -d "/var/log/atmo" ];then\n'
        'mkdir -p /var/log/atmo\n'
        'fi\n'
        'if [ ! -f "/var/log/atmo/deploy.log" ]; then\n'
        'touch /var/log/atmo/deploy.log\n'
        'fi',
        name="./deploy_init_log.sh")


def init(instance, username, password=None, token=None, redeploy=False,
         *args, **kwargs):
    """
    Creates a multi script deployment to prepare and call
    the latest init script
    """
    if not instance:
        raise MissingArgsException("Missing instance argument.")
    if not username:
        raise MissingArgsException("Missing instance argument.")
    token = kwargs.get('token', '')
    if not token:
        token = instance.id
    atmo_init = "/usr/sbin/atmo_init_full.py"
    server_atmo_init = "/api/v1/init_files/v2/atmo_init_full.py"
    logfile = "/var/log/atmo/deploy.log"

    url = "%s%s" % (settings.DEPLOY_SERVER_URL, server_atmo_init)

    script_init = init_log()

    script_deps = package_deps(logfile, username)

    script_wget = wget_file(atmo_init, url, logfile=logfile,
                            attempts=3)

    script_chmod = chmod_ax_file(atmo_init, logfile)

    script_atmo_init = init_script(atmo_init, username, token,
                                   instance, password, redeploy, logfile)

    if redeploy:
        #Redeploy the instance
        script_atmo_init = redeploy_script(atmo_init, username,
                                           instance, logfile)
        script_list = [script_init,
                       script_wget,
                       script_chmod,
                       script_atmo_init]
    else:
        #Standard install
        script_list = [script_init,
                       script_deps,
                       script_wget,
                       script_chmod,
                       script_atmo_init]

    if not settings.DEBUG:
        script_rm_scripts = rm_scripts(logfile=logfile)
        script_list.append(script_rm_scripts)

    return MultiStepDeployment(script_list)

def wrap_script(script_text, script_name):
    """
    NOTE: In current implementation, the script can only be executed, and not
    logged.

    Implementation v2:
    * Write to file
    * Chmod the file
    * Execute and redirect output to stdout/stderr to logfile.
    """
    logfile = "/var/log/atmo/post_boot_scripts.log"
    #kludge: weirdness without the str cast...
    script_text = str(script_text)
    full_script_name = "./deploy_boot_script_%s.sh"
    return ScriptDeployment(
        script_text, name=full_script_name)

