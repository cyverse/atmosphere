"""
Deploy methods for Atmosphere
"""
#from libcloud.compute.deployment import ScriptDeployment
#from libcloud.compute.deployment import MultiStepDeployment
#from libcloud.compute.types import DeploymentError

#from threepio import logger

from rtwo.drivers.common import LoggedScriptDeployment


def mount_volume(device, mount_location=None):
    if not mount_location:
        mount_location = "/vol1"
    return LoggedScriptDeployment("mkdir -p %s\n" % (mount_location)
                                  + "mount %s %s" % (device, mount_location),
                                  name="./deploy_mount_volume.sh",
                                  logfile="/var/log/atmo/deploy.log")


def check_volume(device):
    return LoggedScriptDeployment("tune2fs -l %s" % (device),
                                  name="./deploy_check_volume.sh",
                                  logfile="/var/log/atmo/deploy.log")


def mkfs_volume(device):
    return LoggedScriptDeployment("mkfs.ext3 %s" % (device),
                                  name="./deploy_mkfs_volume.sh",
                                  logfile="/var/log/atmo/deploy.log")
