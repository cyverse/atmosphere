"""
Common functions used by all Openstack managers.
"""
import os
import copy
import subprocess

import glanceclient
from keystoneclient.exceptions import AuthorizationFailure
from keystoneclient import exceptions
from novaclient import client as nova_client
from neutronclient.v2_0 import client as neutron_client

from libcloud.compute.deployment import ScriptDeployment

from threepio import logger
from atmosphere import settings

from service.system_calls import run_command


class LoggedScriptDeployment(ScriptDeployment):

    def __init__(self, script, name=None, delete=False, logfile=None):
        """
        Use this for client-side logging
        """
        super(LoggedScriptDeployment, self).__init__(
            script, name=name, delete=delete)
        if logfile:
            self.script = self.script + " &> %s" % logfile
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


def _connect_to_neutron(*args, **kwargs):
    """
    """
    neutron = neutron_client.Client(*args, **kwargs)
    neutron.format = 'json'
    return neutron


def _connect_to_keystone(*args, **kwargs):
    """
    """
    try:
        version = kwargs.get('version', 'v2.0')
        if version == 'v2.0':
            from keystoneclient.v2_0 import client as ks_client
        else:
            from keystoneclient.v3 import client as ks_client
        keystone = ks_client.Client(*args, **kwargs)
    except AuthorizationFailure as e:
        raise Exception("Authorization Failure: Bad keystone secrets or "
                        "firewall causing a timeout.")
    if version != 'v2.0':
        keystone.management_url = keystone.management_url.replace('v2.0', 'v3')
        keystone.version = 'v3'
    return keystone


def _connect_to_glance(keystone, version='1', *args, **kwargs):
    """
    NOTE: We use v1 because moving up to v2 results in a LOSS OF
    FUNCTIONALITY..
    """
    glance_endpoint = keystone.service_catalog.url_for(
        service_type='image',
        endpoint_type='publicURL')
    auth_token = keystone.service_catalog.get_token()
    glance = glanceclient.Client(version,
                                 endpoint=glance_endpoint,
                                 token=auth_token['id'])
    return glance


def _connect_to_nova(*args, **kwargs):
    kwargs = copy.deepcopy(kwargs)
    version = kwargs.get('version', '1.1')
    region_name = kwargs.get('region_name')
    nova = nova_client.Client(version,
                              kwargs.pop('username'),
                              kwargs.pop('password'),
                              kwargs.pop('tenant_name'),
                              kwargs.pop('auth_url'),
                              kwargs.pop('region_name'),
                              *args, no_cache=True, **kwargs)
    nova.client.region_name = region_name
    return nova


def findall(manager, *args, **kwargs):
    """
        Find all items with attributes matching ``**kwargs``.

        This isn't very efficient: it loads the entire list then filters on
        the Python side.
    """
    found = []
    searches = kwargs.items()

    for obj in manager.list():
        try:
            if all(getattr(obj, attr) == value
                   for (attr, value) in searches):
                found.append(obj)
        except AttributeError:
            continue
    return found


def find(manager, **kwargs):
        """
        Find a single item with attributes matching ``**kwargs``.

        This isn't very efficient: it loads the entire list then filters on
        the Python side.
        """
        rl = findall(manager, **kwargs)
        num = len(rl)

        if num == 0:
            msg = "No %s matching %s." % (manager.resource_class.__name__,
                                          kwargs)
            raise exceptions.NotFound(404, msg)
        elif num > 1:
            raise exceptions.NoUniqueMatch
        else:
            return rl[0]


# SED tools - in-place editing of files on the system
# BE VERY CAREFUL USING THESE -- YOU HAVE BEEN WARNED!


def sed_delete_multi(from_here, to_here, filepath):
    if not os.path.exists(filepath):
        raise Exception("Cannot remove lines from non-existent file: %s" %
                        filepath)
    run_command(
        ["/bin/sed", "-i",
         "/%s/,/%s/d" % (from_here, to_here),
         filepath])


def sed_replace(find, replace, filepath):
    if not os.path.exists(filepath):
        raise Exception("Cannot replace line from non-existent file: %s" %
                        filepath)
    run_command(
        ["/bin/sed", "-i",
         "s/%s/%s/" % (find, replace),
         filepath])


def sed_delete_one(remove_string, filepath):
    if not os.path.exists(filepath):
        raise Exception("Cannot remove line from non-existent file: %s" %
                        filepath)
    run_command(
        ["/bin/sed", "-i",
         "/%s/d" % remove_string,
         filepath])


def sed_append(append_string, filepath):
    if not os.path.exists(filepath):
        raise Exception("Cannot append line to non-existent file: %s" %
                        filepath)
    if _line_exists_in_file(prepend_string, filepath):
        return
    run_command(["/bin/sed", "-i", "$ a\\%s"
                 % append_line, filepath])


def sed_prepend(prepend_string, filepath):
    if not os.path.exists(filepath):
        raise Exception("Cannot prepend line to non-existent file: %s" %
                        filepath)
    if _line_exists_in_file(prepend_string, filepath):
        return
    run_command(["/bin/sed", "-i", "1i %s"
                 % prepend_string, filepath])


def _line_exists_in_file(needle, filepath):
    with open(filepath, 'r') as _file:
        if [line for line in _file.readlines() if needle == line]:
            return True
    return False


def _configure_cloudinit_ubuntu():
    return """#cloud-config
user: ubuntu
manage_etc_hosts: True
disable_root: 0
preserve_hostname: False
datasource_list: [ NoCloud, ConfigDrive, OVF, MAAS, Ec2, CloudStack ]

cloud_init_modules:
 - bootcmd
 - resizefs
 - set_hostname
 - update_hostname
 - update_etc_hosts
 - ca-certs
 - rsyslog
 - ssh

cloud_config_modules:
 - mounts
 - ssh-import-id
 - locale
 - set-passwords
 - grub-dpkg
 - apt-pipelining
 - apt-update-upgrade
 - landscape
 - timezone
 - puppet
 - chef
 - salt-minion
 - mcollective
 - runcmd
 - byobu

cloud_final_modules:
 - rightscale_userdata
 - scripts-per-once
 - scripts-per-boot
 - scripts-per-instance
 - scripts-user
 - keys-to-console
 - phone-home
 - final-message

system_info:
   package_mirrors:
     - arches: [i386, amd64]
       failsafe:
         primary: http://archive.ubuntu.com/ubuntu
         security: http://security.ubuntu.com/ubuntu
       search:
         primary:
           - http://%(ec2_region)s.ec2.archive.ubuntu.com/ubuntu/
           - http://%(availability_zone)s.clouds.archive.ubuntu.com/ubuntu/
         security: []
     - arches: [armhf, armel, default]
       failsafe:
         primary: http://ports.ubuntu.com/ubuntu-ports
         security: http://ports.ubuntu.com/ubuntu-ports
"""


def _configure_cloudinit_centos():
    return """#cloud-config
user: ec2-user
manage_etc_hosts: True
disable_root: 0
preserve_hostname: False
datasource_list: [ NoCloud, ConfigDrive, OVF, MAAS, Ec2, CloudStack ]

cloud_init_modules:
 - bootcmd
 - resizefs
 - set_hostname
 - update_hostname
 - update_etc_hosts
 - rsyslog
 - ssh

cloud_config_modules:
 - mounts
 - ssh-import-id
 - locale
 - set-passwords
 - timezone
 - puppet
 - chef
 - salt-minion
 - runcmd

cloud_final_modules:
 - rightscale_userdata
 - scripts-per-once
 - scripts-per-boot
 - scripts-per-instance
 - scripts-user
 - keys-to-console
 - phone-home
 - final-message
"""


def prepare_cloudinit_script():
    """
    The most complete list of cloud-init modules can be found here:
    http://bit.ly/skLuOi #shortened for pep8
    """
    prepared_script = """#cloud-config
# final_message
# default: cloud-init boot finished at $TIMESTAMP. Up $UPTIME seconds
# this message is written by cloud-final when the system is finished
# its first boot
final_message: "The system is finally up, after $UPTIME seconds"

# configure where output will go
# 'output' entry is a dict with 'init', 'config', 'final' or 'all'
# entries.  Each one defines where
#  cloud-init, cloud-config, cloud-config-final or all output will go
# each entry in the dict can be a string, list or dict.
#  if it is a string, it refers to stdout and stderr
#  if it is a list, entry 0 is stdout, entry 1 is stderr
#  if it is a dict, it is expected to have 'output' and 'error' fields
# default is to write to console only
# the special entry "&1" for an error means "same location as stdout"
#  (Note, that '&1' has meaning in yaml, so it must be quoted)
output:
 all:
   output: "| tee /var/log/atmosphere-cloud-init.log"
   error: "&1"

# phone_home: if this dictionary is present, then the phone_home
# cloud-config module will post specified data back to the given
# url
# default: none
# phone_home:
#  url: http://my.foo.bar/$INSTANCE/
#  post: all
#  tries: 10
#
phone_home:
 url: %s
 post: all
 tries: 10
""" % (settings.INSTANCE_SERVICE_URL)

    logger.info(prepared_script)
    return prepared_script


def install_cloudinit(mount_point, distro='CentOS'):
    if distro == 'CentOS':
        #Install it
        chroot_local_image(mount_point, mount_point, [
            ["/bin/bash", "-c", "yum install -qy cloud-init"]],
            bind=True, mounted=True, keep_mounted=True)
        #Get CentOS default overrides
        cloud_config = _configure_cloudinit_centos()
    else:
        #For Ubuntu:
        chroot_local_image(mount_point, mount_point, [
            ["/bin/bash", "-c", "apt-get install -qy cloud-init"]],
            bind=True, mounted=True, keep_mounted=True)
        cloud_config = _configure_cloudinit_ubuntu()

    #Overwrite the cloud.cfg defaults
    mounted_filepath = os.path.join(mount_point, 'etc/cloud/cloud.cfg')
    with open(mounted_filepath, 'w') as cloud_config_file:
        cloud_config_file.write(cloud_config)

    #If Ubuntu, remove the cloud.cfg.d for dpkg, it is not properly configured.
    if distro != 'CentOS':
        mounted_config_d = os.path.join(mount_point,
                                        'etc/cloud/cloud.cfg.d/90_dpkg.cfg')
        if os.path.exists(mounted_config_d):
            os.remove(mounted_config_d)


def chroot_local_image(image_path, mount_point, commands_list,
                       bind=False, mounted=False, keep_mounted=False):
    """
    Accepts a list of commands (See Popen), runs them in a chroot
    Will mount the image if image_path exists && mounted=False
    Will bind /proc, /dev, /sys for the chroot if bind=True
    Will leave mounted on exit if keep_mounted=True
    """
    #Prepare the paths (Ignore if already mounted)
    if not mounted and not os.path.exists(image_path)\
            and not 'dev/loop' in image_path:
        logger.error("Could not find local image!")
        raise Exception("Image file not found")

    if not os.path.exists(mount_point):
        os.makedirs(mount_point)
    #Mount the directory
    if not mounted:
        run_command(['mount', '-o', 'loop', image_path, mount_point])
    #If bind is required, prepare for mount
    if bind:
        proc_dir = os.path.join(mount_point, 'proc/')
        sys_dir = os.path.join(mount_point, 'sys/')
        dev_dir = os.path.join(mount_point, 'dev/')
        run_command(['mount', '-t', 'proc', '/proc', proc_dir])
        run_command(['mount', '-t', 'sysfs', '/sys', sys_dir])
        run_command(['mount', '-o', 'bind', '/dev',  dev_dir])
    for commands in commands_list:
        command_list = ['chroot', mount_point]
        command_list.extend(commands)
        run_command(command_list)
    #If bind was used, unmount sys, dev, and proc
    if bind:
        run_command(['umount', proc_dir])
        run_command(['umount', sys_dir])
        run_command(['umount', dev_dir])
    if not keep_mounted:
        run_command(['umount', mount_point])


def get_ranges(uid_number, inc=0):
    """
    Return two block ranges to be used to create subnets for
    Atmosphere users.

    NOTE: If you change MAX_SUBNET then you should likely change
    the related math.
    """
    MAX_SUBNET = 4064  # Note 16 * 256
    n = uid_number % MAX_SUBNET

    #16-31
    block1 = (n + inc) % 16 + 16

    #1-254
    block2 = ((n + inc) / 16) % 254 + 1

    return (block1, block2)


def get_default_subnet(username, inc=0):
    """
    Return the default subnet for the username and provider.

    Add and mod by inc to allow for collitions.
    """
    uid_number = get_uid_number(username)

    if uid_number:
        (block1, block2) = get_ranges(uid_number, inc)
    else:
        (block1, block2) = get_ranges(0, inc)

    if username == "jmatt":
        return "172.16.42.0/24"  # /flex
    else:
        return "172.%s.%s.0/24" % (block1, block2)


def get_driver(driverCls, provider, identity):
    """
    Create a driver object from a class, provider and identity.
    """
    from rtwo import compute
    compute.initialize()
    driver = driverCls(provider, identity)
    if driver:
        return driver
