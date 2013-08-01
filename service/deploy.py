"""
Deploy methods for Atmosphere
"""
from libcloud.compute.deployment import ScriptDeployment
#from libcloud.compute.deployment import MultiStepDeployment
#from libcloud.compute.types import DeploymentError

#from threepio import logger

from rtwo.drivers.common import LoggedScriptDeployment


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
