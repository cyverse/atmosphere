"""
Deploy methods for Atmosphere
"""
from libcloud.compute.deployment import ScriptDeployment
#from libcloud.compute.deployment import MultiStepDeployment
#from libcloud.compute.types import DeploymentError

#from threepio import logger


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


def install_util_linux(distro='ubuntu'):
    return ScriptDeployment(
        "%s install -qy utils-linux"
        % 'apt-get' if 'ubuntu' in distro.to_lower() else 'yum',
        name="./deploy_freeze_instance.sh")


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
    return ScriptDeployment(step.script, name="./" + step.get_script_name())
