"""
Common functions used by all Openstack managers 
"""
import os
import subprocess

import glanceclient
from keystoneclient.v3 import client as ks_client
from novaclient import client as nova_client

from libcloud.compute.deployment import ScriptDeployment

from threepio import logger

class LoggedScriptDeployment(ScriptDeployment):


    def __init__(self, script, name=None, delete=False, logfile=None):
        """
        Use this for client-side logging
        """
        super(LoggedScriptDeployment, self).__init__(
                script, name=name, delete=delete)
        if logfile:
            self.script = self.script + " &> %s" % logfile
        logger.info(self.script)

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


def _connect_to_keystone(*args, **kwargs):
    """
    """
    keystone = ks_client.Client(*args, **kwargs)
    keystone.management_url = keystone.management_url.replace('v2.0','v3')
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

def _connect_to_nova(version='1.1', *args, **kwargs):
    region_name = kwargs.get('region_name'),
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
            msg = "No %s matching %s." % (manager.resource_class.__name__, kwargs)
            raise exceptions.NotFound(404, msg)
        elif num > 1:
            raise exceptions.NoUniqueMatch
        else:
            return rl[0]


"""
SED tools - in-place editing of files on the system
BE VERY CAREFUL USING THESE -- YOU HAVE BEEN WARNED!
"""
def sed_delete_multi(from_here,to_here,filepath):
    if not os.path.exists(filepath):
        raise Exception("Cannot remove lines from non-existent file: %s" %
                filepath)
    run_command(
        ["/bin/sed", "-i",
         "/%s/,/%s/d" % (from_here, to_here),
         filepath])

def sed_replace(find,replace,filepath):
    if not os.path.exists(filepath):
        raise Exception("Cannot replace line from non-existent file: %s" %
                filepath)
    run_command(
        ["/bin/sed", "-i", 
         "s/%s/%s/" % (find,replace),
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
    with open(filepath,'r') as _file:
        if [line for line in _file.readlines()
            if needle == line]:
            return True
    return False

"""
Running general system commands, wrapped around a logger
"""
def run_command(commandList, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=None):
    """
    Using Popen, run any command at the system level and record the output and error streams
    """
    out = None
    err = None
    logger.debug("Running Command:<%s>" % ' '.join(commandList))
    try:
        if stdin:
            proc = subprocess.Popen(commandList, stdout=stdout, stderr=stderr, stdin=subprocess.PIPE)
        else:
            proc = subprocess.Popen(commandList, stdout=stdout, stderr=stderr)
        out,err = proc.communicate(input=stdin)
    except Exception, e:
        logger.error(e)
    if stdin:
        logger.debug("STDIN: %s" % stdin)
    logger.debug("STDOUT: %s" % out)
    logger.debug("STDERR: %s" % err)
    return (out,err)

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
        proc_dir = os.path.join(mount_point,'proc/')
        sys_dir = os.path.join(mount_point,'sys/')
        dev_dir = os.path.join(mount_point,'dev/')
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

