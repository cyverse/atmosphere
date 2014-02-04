"""
Deploy methods for Atmosphere
"""
from os.path import basename

from libcloud.compute.deployment import ScriptDeployment
from libcloud.compute.deployment import MultiStepDeployment

from threepio import logger

from atmosphere import settings
from atmosphere.settings import secrets


#
# Deployment Classes
#
class LoggedScriptDeployment(ScriptDeployment):

    def __init__(self, script, name=None, delete=False, logfile=None):
        """
        Use this for client-side logging
        """
        super(LoggedScriptDeployment, self).__init__(
            script, name=name, delete=delete)
        if logfile:
            self.script = self.script + " >> %s 2>&1" % logfile
        #logger.info(self.script)

    def run(self, node, client):
        """
        Server-side logging
        """
        node = super(LoggedScriptDeployment, self).run(node, client)
        if self.stdout:
            logger.debug('%s (%s)STDOUT: %s' % (node.id, self.name,
                                                self.stdout))
        if self.stderr:
            logger.warn('%s (%s)STDERR: %s' % (node.id, self.name,
                                               self.stderr))
        return node


#
# Specific Deployments
#

def sync_instance():
    return ScriptDeployment("sync", name="./deploy_sync_instance.sh")


def get_distro(distro='ubuntu'):
    return ScriptDeployment("cat /etc/*-release",
                            name="./deploy_get_distro.sh")


def build_script(script_input, name=None):
    return ScriptDeployment(script_input, name=name)


def install_base_requirements(distro='ubuntu'):
    script_txt = "%s install -qy utils-linux %s"\
        % ('apt-get' if 'ubuntu' in distro.to_lower() else 'yum',
           '' if 'ubuntu' in distro.to_lower() else 'python-simplejson')
    return ScriptDeployment(script_txt,
        name="./deploy_base_requirements.sh")


def freeze_instance(sleep_time=45):
    return ScriptDeployment(
        "fsfreeze -f / && sleep %s && fsfreeze -u /" % sleep_time,
        name="./deploy_freeze_instance.sh")


def mount_volume(device, mount_location):
    return ScriptDeployment("mkdir -p %s\n" % (mount_location)
                            + "mount %s %s" % (device, mount_location),
                            name="./deploy_mount_volume.sh")


def check_mount():
    return ScriptDeployment("mount",
                            name="./deploy_check_mount.sh")


def check_volume(device):
    return ScriptDeployment("tune2fs -l %s" % (device),
                            name="./deploy_check_volume.sh")


def mkfs_volume(device):
    return ScriptDeployment("mkfs.ext3 %s" % (device),
                            name="./deploy_mkfs_volume.sh")


def umount_volume(mount_location):
    return ScriptDeployment("umount %s" % (mount_location),
                            name="./deploy_umount_volume.sh")


def lsof_location(mount_location):
    return ScriptDeployment("lsof | grep %s" % (mount_location),
                            name="./deploy_lsof_location.sh")


def step_script(step):
    script = str(step.script)
    if not script.startswith("#!"):
        script = "#! /usr/bin/env bash\n" + script
    return ScriptDeployment(script, name="./" + step.get_script_name())


def wget_file(filename, url, logfile=None):
    name = './deploy_wget_%s.sh' % (basename(filename))
    return LoggedScriptDeployment(
        "wget -O %s %s" % (filename, url),
        name=name,
        logfile=logfile)


def chmod_ax_file(filename, logfile=None):
    return LoggedScriptDeployment(
        "chmod a+x %s" % filename,
        name='./deploy_chmod_ax.sh',
        logfile=logfile)


def package_deps(logfile=None):
    #These requirements are for Editors, Shell-in-a-box, etc.
    do_ubuntu = "apt-get update;apt-get install -y emacs vim wget "\
                + "language-pack-en make gcc g++ gettext texinfo "\
                + "autoconf automake"
    do_centos = "yum install -y emacs vim-enhanced wget make "\
                + "gcc gettext texinfo autoconf automake python-simplejson"
    return LoggedScriptDeployment(
        "distro_cat=`cat /etc/*-release`\n"
        + "if [[ $distro_cat == *Ubuntu* ]]; then\n"
        + do_ubuntu
        + "\nelse if [[ $distro_cat == *CentOS* ]];then\n"
        + do_centos
        + "\nfi\nfi",
        name="./deploy_package_deps.sh",
        logfile=logfile)


def init_script(filename, username, token, instance, password, logfile=None):
        awesome_atmo_call = "%s --service_type=%s --service_url=%s"
        awesome_atmo_call += " --server=%s --user_id=%s"
        awesome_atmo_call += " --token=%s --name=\"%s\""
        awesome_atmo_call += " --vnc_license=%s"
        awesome_atmo_call %= (
            filename,
            "instance_service_v1",
            settings.INSTANCE_SERVICE_URL,
            settings.SERVER_URL,
            username,
            token,
            instance.name,
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


def init_log():
    return ScriptDeployment(
        'if [ ! -d "/var/log/atmo" ];then\n'
        'mkdir -p /var/log/atmo\n'
        'fi\n'
        'if [ ! -f "/var/log/atmo/deploy.log" ]; then\n'
        'touch /var/log/atmo/deploy.log\n'
        'fi',
        name="./deploy_init_log.sh")


def init(instance, username, password=None, *args, **kwargs):
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
        server_atmo_init = "/init_files/v2/atmo_init_full.py"
        logfile = "/var/log/atmo/deploy.log"

        url = "%s%s" % (settings.SERVER_URL, server_atmo_init)

        script_init = init_log()

        script_deps = package_deps()

        script_wget = wget_file(atmo_init, url, logfile)

        script_chmod = chmod_ax_file(atmo_init, logfile)

        script_atmo_init = init_script(atmo_init, username, token,
                                       instance, password, logfile)

        #TODO: REMOVE THIS LINE BEFORE 2/4/14
        #script_rm_scripts = rm_scripts(logfile=logfile)

        return MultiStepDeployment([script_init,
                                    script_deps,
                                    script_wget,
                                    script_chmod,
                                    script_atmo_init])

        # kwargs.update({'deploy': msd})

        # private_key = "/opt/dev/atmosphere/extras/ssh/id_rsa"
        # kwargs.update({'ssh_key': private_key})

        # kwargs.update({'timeout': 120})

        # return self.deploy_to(instance, *args, **kwargs)
