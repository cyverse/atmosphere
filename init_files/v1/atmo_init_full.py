#!/usr/bin/env python
"""
Debugging atmo_init_full locally:
    cd /usr/sbin
    touch __init__.py
    python
    >>> import atmo_init_full
    >>>
"""
import getopt
import logging
import os
try:
    import json
except ImportError:
    import simplejson as json
import errno
import re
import time
import urllib2
import subprocess
import sys
try:
    from hashlib import sha1
except ImportError:
    # Support for python 2.4
    from sha import sha as sha1

ATMOSERVER = ""
USER_HOME_DIR = ""
eucalyptus_meta_server = 'http://128.196.172.136:8773/latest/meta-data/'
openstack_meta_server = 'http://169.254.169.254/latest/meta-data/'
SCRIPT_VERSION = "v2"


def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:
        # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


def touch(fname, times=None):
    f = open(fname, 'a')
    f.close()
    os.utime(fname, times)


def init_logs(log_file):
    # NOTE: Can't use run_command until logs are initialized
    mkdir_p('/var/log/atmo/')
    touch('/var/log/atmo/atmo_init_full.log')
    format = "%(asctime)s %(name)s-%(levelname)s "\
             + "[%(pathname)s %(lineno)d] %(message)s"
    logging.basicConfig(
        level=logging.DEBUG,
        format=format,
        filename=log_file,
        filemode='a+')


def download_file(url, fileLoc, retry=False, match_hash=None):
    waitTime = 0
    attempts = 0
    contents = None
    logging.debug('Downloading file: %s' % url)
    while True:
        attempts += 1
        logging.debug('Attempt: %s, Wait %s seconds' % (attempts, waitTime))
        time.sleep(waitTime)
        # Exponential backoff * 10s = 20s,40s,80s,160s,320s...
        waitTime = 10 * 2**attempts
        try:
            resp = urllib2.urlopen(url)
        except Exception as e:
            logging.exception("Failed to download URL: %s" % url)
            resp = None

        # Download file on success
        if resp is not None and resp.code == 200:
            contents = resp.read()
        # EXIT condition #1: Non-empty file found
        if contents is not None and len(contents) != 0:
            logging.debug('Downloaded file')
            break
        # EXIT condition #2: Don't want to try again
        if not retry:
            break
        # Retry condition: Retry is true && file is empty
    # Save file if hash matches
    try:
        file_hash = sha1(contents).hexdigest()
    except Exception as e:
        file_hash = ""
        logging.exception("Failed to create sha1 hash for file")
    # Don't save file if hash exists and doesnt match..
    if match_hash and match_hash != file_hash:
        logging.warn(
            "Error, The downloaded file <%s - SHA1:%s> "
            "does not match expected SHA1:%s"
            % (url, file_hash, match_hash))
        return ""
    logging.debug('Saving url:%s to file: %s' % (url, fileLoc))
    f = open(fileLoc, "w")
    f.write(contents)
    f.close()
    return contents


def set_hostname(hostname, distro):
    # Set the hostname once
    run_command(['/bin/hostname', hostname])
    # And set a dhcp exithook to keep things running on suspend/stop
    if is_rhel(distro):
        run_command(['/usr/bin/yum', '-qy', 'install', 'dhcp'])
        download_file(
            '%s/init_files/%s/centos_hostname-exit-hook.sh' %
            (ATMOSERVER, SCRIPT_VERSION),
            "/etc/dhclient-exit-hooks", match_hash='')
        run_command(['/bin/chmod', 'a+x', "/etc/dhclient-exit-hooks"])
    else:
        download_file(
            '%s/init_files/%s/ubuntu_hostname-exit-hook.sh' %
            (ATMOSERVER, SCRIPT_VERSION),
            "/etc/dhcp/dhclient-exit-hooks.d/hostname", match_hash='')
        run_command(
            ['/bin/chmod', 'a+x', "/etc/dhcp/dhclient-exit-hooks.d/hostname"])


def get_hostname(instance_metadata):
    # As set by atmosphere in the instance metadata
    hostname = instance_metadata.get('meta', {}).get('public-hostname')
    # As returned by metadata service
    if not hostname:
        hostname = instance_metadata.get('public-hostname')
    if not hostname:
        hostname = instance_metadata.get('local-hostname')
    if not hostname:
        hostname = instance_metadata.get('hostname')
    # No hostname, look for public ip instead
    if not hostname:
        return get_public_ip(instance_metadata)
    return hostname


def get_public_ip(instance_metadata):
    """
    Checks multiple locations in metadata for the IP address
    """
    ip_addr = instance_metadata.get('public-ipv4')
    if not ip_addr:
        ip_addr = instance_metadata.get('local-ipv4')
    if not ip_addr:
        ip_addr = 'localhost'
    return ip_addr


def get_distro():
    if os.path.isfile('/etc/redhat-release'):
        return 'rhel'
    else:
        return 'ubuntu'


def run_command(commandList, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                stdin=None, dry_run=False, shell=False, bash_wrap=False,
                block_log=False):
    if bash_wrap:
        # Wrap the entire command in '/bin/bash -c',
        # This can sometimes help pesky commands
        commandList = ['/bin/bash', '-c', ' '.join(commandList)]
    """
    NOTE: Use this to run ANY system command, because its wrapped around a loggger
    Using Popen, run any command at the system level and record the output and error streams
    """
    out = None
    err = None
    cmd_str = ' '.join(commandList)
    if dry_run:
        # Bail before making the call
        logging.debug("Mock Command: %s" % cmd_str)
        return ('', '')
    try:
        if stdin:
            proc = subprocess.Popen(commandList, stdout=stdout, stderr=stderr,
                                    stdin=subprocess.PIPE, shell=shell)
        else:
            proc = subprocess.Popen(commandList, stdout=stdout, stderr=stderr,
                                    shell=shell)
        out, err = proc.communicate(input=stdin)
    except Exception as e:
        logging.exception(e)
    if block_log:
        # Leave before we log!
        return (out, err)
    if stdin:
        logging.debug("%s STDIN: %s" % (cmd_str, stdin))
    logging.debug("%s STDOUT: %s" % (cmd_str, out))
    logging.debug("%s STDERR: %s" % (cmd_str, err))
    return (out, err)


def in_etc_group(filename, val):
    for line in open(filename, 'r').read().split('\n'):
        if 'users' in line and val in line:
            return True
    return False


def add_etc_group(user):
    run_command(["/bin/sed -i 's/users:x:.*/&%s,/' /etc/group" % (user, )],
                bash_wrap=True)


def is_updated_test(filename):
    if '## Atmosphere System' in open(filename).read():
        return True
    return False


def file_contains(filename, val):
    return val in open(filename, 'r').read()


def etc_skel_bashrc(user):
    filename = "/etc/skel/.bashrc"
    if not is_updated_test(filename):
        # TODO: Should this be $USER instead of %s?
        append_to_file(filename, """
export IDS_HOME="/irods/data.iplantc.org/iplant/home/%s"
alias ids_home="cd $IDS_HOME"
""" % user)


def text_in_file(filename, text):
    f = open(filename, 'r')
    whole_file = f.read()
    if text in whole_file:
        f.close()
        return True
    f.close()
    return False


def write_to_file(filename, text):
    try:
        logging.debug("Text to input: %s" % text)
        f = open(filename, "w")
        f.write(text)
        f.close()
    except Exception as e:
        logging.exception("Failed to write to %s" % filename)


def append_to_file(filename, text):
    try:
        if text_in_file(filename, text):
            return
        f = open(filename, "a")
        f.write("## Atmosphere System\n")
        f.write(text)
        f.write("\n")
        f.write("## End Atmosphere System\n")
        f.close()
    except Exception as e:
        logging.exception("Failed to append to %s" % filename)
        logging.exception("Failed to append text: %s" % text)


def in_sudoers(user):
    out, err = run_command(['sudo -l -U %s' % user], shell=True)
    if 'not allowed to run sudo' in out:
        return False
    if 'unknown user' in err:
        return False
    lines = out.split('\n')
    line_match = '%s may run the following' % user
    for idx, line in enumerate(lines):
        if line_match in line:
            allowed_idx = idx
    root_allowed = lines[allowed_idx + 1:]
    for line in root_allowed:
        if line:
            return True
    return False


def add_sudoers(user):
    atmo_sudo_file = "/etc/sudoers"
    append_to_file(
        atmo_sudo_file,
        "%s ALL=(ALL)ALL" % user)
    os.chmod(atmo_sudo_file, 0o440)


def restart_ssh(distro):
    if is_rhel(distro):
        run_command(["/etc/init.d/sshd", "restart"])
    else:
        run_command(["/etc/init.d/ssh", "restart"])


def set_root_password(root_password, distro):
    if is_rhel(distro):
        run_command(["passwd", "--stdin", "root"], stdin=root_password,
                    block_log=True)
    else:
        run_command(["chpasswd"], stdin="root:%s" % root_password,
                    block_log=True)

    if text_in_file('/etc/ssh/sshd_config', 'PermitRootLogin'):
        run_command([
            '/bin/sed', '-i',
            "s/PermitRootLogin\s*no$/PermitRootLogin yes/",
            '/etc/ssh/sshd_config'])
        run_command([
            '/bin/sed', '-i',
            "s/PermitRootLogin\s*without-password$/PermitRootLogin yes/",
            '/etc/ssh/sshd_config'])
    else:
        append_to_file("/etc/ssh/sshd_config", "PermitRootLogin yes")
    restart_ssh(distro)


def ssh_config(distro):
    append_to_file(
        "/etc/ssh/sshd_config",
        "AllowGroups users core-services root")
    restart_ssh(distro)


def get_metadata_keys(metadata):
    keys = []
    # Eucalyptus/Openstack key (Traditional metadata API)
    euca_key = _make_request('%s%s' % (eucalyptus_meta_server,
                                       "public-keys/0/openssh-key/"))
    os_key = _make_request('%s%s' % (openstack_meta_server,
                                     "public-keys/0/openssh-key/"))
    if euca_key:
        keys.append(euca_key)
    if os_key:
        keys.append(os_key)
    # JSON metadata API
    public_keys = metadata.get('public_keys', {})
    for k, v in public_keys.items():
        keys.append(v.replace('\n', ''))  # Includes a newline
    return keys


def get_metadata():
    openstack_json_metadata = 'http://169.254.169.254/openstack/'\
                              'latest/meta_data.json'
    metadata = collect_metadata(eucalyptus_meta_server)
    if not metadata:
        metadata = collect_metadata(openstack_meta_server)
        metadata.update(
            collect_json_metadata(openstack_json_metadata))
    return metadata


def collect_json_metadata(metadata_url):
    content = _make_request(metadata_url)
    meta_obj = json.loads(content)
    return meta_obj


def _make_request(request_url):
    try:
        logging.info("Making request to %s" % request_url)
        resp = urllib2.urlopen(request_url)
        content = resp.read()
        return content
    except Exception as e:
        logging.exception("Could not retrieve meta-data for instance")
        return None


def collect_metadata(meta_endpoint):
    metadata = {}
    meta_list = []
    content = _make_request(meta_endpoint)
    meta_list = content.split('\n')

    for meta_key in meta_list:
        if not meta_key:
            continue
        try:
            meta_value = _make_request('%s%s' % (meta_endpoint, meta_key))
            if meta_key.endswith('/'):
                meta_values = meta_value.split('\n')
                for value in meta_values:
                    print "new meta: %s%s" % (meta_key, value)
                    meta_list.append("%s%s" % (meta_key, value))
            else:
                metadata[meta_key] = meta_value
        except Exception as e:
            logging.exception("Metadata retrieval error")
            metadata[meta_key] = None
    return metadata


def mount_storage():
    """
    In addition to the 'root disk' (Generally small)
    An instance usually has epehemeral disk storage
    This is TEMPORARY space you can use while working on your instance
    It is deleted when the instance is terminated.

    #TODO: Refactor.
    """
    try:
        logging.debug("Mount test")
        (out, err) = run_command(['/sbin/fdisk', '-l'])
        dev_1 = None
        dev_2 = None
        if 'sda1' in out:
            # Eucalyptus CentOS format
            dev_1 = 'sda1'
            dev_2 = 'sda2'
        elif 'xvda1' in out:
            # Eucalyptus Ubuntu format
            dev_1 = 'xvda1'
            dev_2 = 'xvda2'
        elif 'vda' in out:
            # Openstack format for Root/Ephem. Disk
            dev_1 = 'vda'
            dev_2 = 'vdb'
        else:
            # Harddrive format cannot be determined..
            logging.warn("Could not determine disks from fdisk output:%s"
                         % out)
        outLines = out.split('\n')
        for line in outLines:
            r = re.compile(', (.*?) bytes')
            match = r.search(line)
            if dev_1 in line:
                dev_1_size = match.group(1)
            elif dev_2 in line:
                dev_2_size = match.group(1)
        if int(dev_2_size) > int(dev_1_size):
            logging.warn(
                "%s is larger than %s, Mounting %s to home"
                % (dev_2, dev_1, dev_2))
            run_command(["/bin/mount", "-text3", "/dev/%s" % dev_2, "/home"])
    except Exception as e:
        logging.exception("Could not mount storage. Error below:")


def vnc(user, distro, license=None):
    try:
        if not os.path.isfile('/usr/bin/xterm'):
            logging.debug("Could not find a GUI on this machine, "
                          "Skipping VNC Install.")
            return
        # ASSERT: VNC server installed on this machine
        if is_rhel(distro):
            run_command(['/usr/bin/yum', '-qy', 'remove', 'vnc-E',
                         'realvnc-vnc-server'])
            download_file(
                '%s/init_files/%s/VNC-Server-5.1.0-Linux-x64.rpm'
                % (ATMOSERVER, SCRIPT_VERSION),
                "/opt/VNC-Server-5.1.0-Linux-x64.rpm",
                match_hash='5e62e4d456ceb2b473509bbd0064694d9820a738')
            run_command(['/bin/rpm', '-Uvh',
                         '/opt/VNC-Server-5.1.0-Linux-x64.rpm'])
            run_command(['/bin/sed', '-i',
                         "'$a account    include      system-auth'",
                         '/etc/pam.d/vncserver.custom'], bash_wrap=True)
            run_command(['/bin/sed', '-i',
                         "'$a password   include      system-auth'",
                         '/etc/pam.d/vncserver.custom'], bash_wrap=True)
        else:
            download_file(
                '%s/init_files/%s/VNC-Server-5.1.0-Linux-x64.deb'
                % (ATMOSERVER, SCRIPT_VERSION),
                "/opt/VNC-Server-5.1.0-Linux-x64.deb",
                match_hash='96050939b98a0d91c6f293401230dbd22922ec2e')
            run_command(['/usr/bin/dpkg', '-i',
                         '/opt/VNC-Server-5.1.0-Linux-x64.deb'])
            new_file = open('/etc/pam.d/vncserver.custom', 'w')
            new_file.write("auth include  common-auth")
            new_file.close()
            new_file = open('/etc/vnc/config.d/common.custom', 'w')
            new_file.write("PamApplicationName=vncserver.custom")
            new_file.close()
        time.sleep(1)
        run_command(['/usr/bin/vnclicense', '-add', license], block_log=True)
        download_file(
            '%s/init_files/%s/vnc-config.sh' % (ATMOSERVER, SCRIPT_VERSION),
            os.path.join(USER_HOME_DIR, 'vnc-config.sh'),
            match_hash='9bbb495ad67bb3117349a637e5716ba08a213713')
        run_command(['/bin/chmod', 'a+x',
                     os.path.join(USER_HOME_DIR, 'vnc-config.sh')])
        run_command([os.path.join(USER_HOME_DIR, 'vnc-config.sh')])
        run_command(['/bin/rm',
                     os.path.join(USER_HOME_DIR, 'vnc-config.sh')])
        if os.path.exists('/tmp/.X1-lock'):
            run_command(['/bin/rm', '/tmp/.X1-lock'])
        if os.path.exists('/tmp/.X11-unix'):
            run_command(['/bin/rm', '-rf', '/tmp/.X11-unix'])
        run_command(['/bin/mkdir', '/tmp/.X11-unix'])
        run_command(['/bin/chmod', 'a+rwxt', '/tmp/.X11-unix'])
        run_command(['/bin/su', '%s' % user, '-c', '/usr/bin/vncserver'])
    except Exception as e:
        logging.exception('Failed to install VNC')


def parrot_install(distro):
    try:
        cctools_file = 'cctools-3.7.2-x86_64-redhat5.tar.gz'
        download_file(
            'http://www.iplantcollaborative.org/sites/default/files'
            + '/atmosphere/cctools/%s' % (cctools_file),
            '/opt/%s' % (cctools_file),
            match_hash='04e0ef9e11e8ef7ac28ef694fd57e75b09455084')
        run_command(
            ['/bin/tar', 'zxf',
             '/opt/%s' % (cctools_file),
             '-C', '/opt/'])
        if not is_rhel(distro):
            run_command(['/usr/bin/apt-get', '-qy', 'install',
                         'libssl-dev'])
            # Ubuntu needs linking
            run_command(
                ['/bin/ln', '-s',
                 '/lib/x86_64-linux-gnu/libssl.so.1.0.0',
                 '/lib/x86_64-linux-gnu/libssl.so.6'])
            run_command(
                ['/bin/ln', '-s',
                 '/lib/x86_64-linux-gnu/libcrypto.so.1.0.0',
                 '/lib/x86_64-linux-gnu/libcrypto.so.6'])
        # link all files

        for f in os.listdir("/opt/cctools/bin"):
            try:
                link_f = os.path.join("/usr/local/bin", f)
                logging.debug(link_f)
                if os.path.exists(link_f):
                    os.remove(link_f)
                logging.debug(os.path.join("/opt/cctools/bin", f))
                os.symlink(os.path.join("/opt/cctools/bin", f), link_f)
            except Exception:
                logging.debug(
                    "Problem linking /opt/cctools/bin to /usr/local/bin")
    except Exception as e:
        logging.exception("Failed to install parrot. Details below:")


def iplant_files(distro):
    parrot_install(distro)
    download_file(
        'http://www.iplantcollaborative.org/sites/default/files/atmosphere/'
        + 'fuse.conf', '/etc/fuse.conf',
        match_hash='21d4f3e735709827142d77dee60befcffd2bf5b1')

    download_file(
        "http://www.iplantcollaborative.org/sites/default/files/atmosphere/"
        + "atmoinfo", "/usr/local/bin/atmoinfo",
        match_hash="0f6426df41a5fe139515079060ab1758e844e20c")
    run_command(["/bin/chmod", "a+x", "/usr/local/bin/atmoinfo"])

    download_file(
        "http://www.iplantcollaborative.org/sites/default/files/atmosphere/"
        + "xprintidle", "/usr/local/bin/xprintidle",
        match_hash="5c8b63bdeab349cff6f2bf74277e9143c1a2254f")
    run_command(["/bin/chmod", "a+x", "/usr/local/bin/xprintidle"])

    download_file(
        "http://www.iplantcollaborative.org/sites/default/files/atmosphere/"
        + "atmo_check_idle.py",
        "/usr/local/bin/atmo_check_idle.py",
        match_hash="ab37a256e15ef5f529b4f4811f78174265eb7aa0")
    run_command(["/bin/chmod", "a+x", "/usr/local/bin/atmo_check_idle.py"])

    run_command(["/bin/mkdir", "-p", "/opt/irodsidrop"])
    download_file("http://www.iplantc.org/sites/default/files/irods/idrop.jar",
                  "/opt/irodsidrop/idrop-latest.jar",
                  match_hash="275cc7fb744b0f29caa7b276f689651a2159c23e")
    download_file(
        "http://www.iplantcollaborative.org/sites/default/files/"
        + "idroprun.sh.txt", "/opt/irodsidrop/idroprun.sh",
        match_hash="0e9cec8ce1d38476dda1646631a54f6b2ddceff5")
    run_command(['/bin/chmod', 'a+x', '/opt/irodsidrop/idroprun.sh'])
    download_file('%s/init_files/%s/iplant_backup.sh'
                  % (ATMOSERVER, SCRIPT_VERSION),
                  "/usr/local/bin/iplant_backup",
                  match_hash='72925d4da5ed30698c81cc95b0a610c8754500e7')
    run_command(['/bin/chmod', 'a+x', "/usr/local/bin/iplant_backup"])


def line_in_file(needle, filename):
    found = False
    f = open(filename, 'r')
    for line in f:
        if needle in line:
            found = True
            break
    f.close()
    return found


def modify_rclocal(username, distro, hostname='localhost'):
    try:
        if is_rhel(distro):
            distro_rc_local = '/etc/rc.d/rc.local'
        else:
            distro_rc_local = '/etc/rc.local'

        # This temporary file will be re-written each time.
        atmo_rclocal_path = '/etc/rc.local.atmo'

        # First we must make sure its included in our original RC local
        if not line_in_file(atmo_rclocal_path, distro_rc_local):
            open_file = open(distro_rc_local, 'a')
            open_file.write('if [ -x %s ]; then\n'
                            '\t%s\n'
                            'fi\n' % (atmo_rclocal_path, atmo_rclocal_path))
            open_file.close()
        # If there was an exit line, it must be removed
        if line_in_file('exit', distro_rc_local):
            run_command(['/bin/sed', '-i',
                         "s/exit.*//", '/etc/rc.local'])
        # Intentionally REPLACE the entire contents of file on each run
        atmo_rclocal = open(atmo_rclocal_path, 'w')
        atmo_rclocal.write('#!/bin/sh -e\n'
                           'depmod -a\n'
                           'modprobe acpiphp\n'
                           'hostname %s\n'  # public_ip
                           '/bin/su %s -c /usr/bin/vncserver\n'  # username
                           '/usr/bin/nohup /usr/local/bin/shellinaboxd -b -t '
                           '-f beep.wav:/dev/null '
                           '> /var/log/atmo/shellinaboxd.log 2>&1 &\n'
                           # Add new rc.local commands here
                           # And they will be excecuted on startup
                           # Don't forget the newline char
                           % (hostname, username))
        atmo_rclocal.close()
        os.chmod(atmo_rclocal_path, 0o755)
    except Exception as e:
        logging.exception("Failed to write to rc.local")


def shellinaboxd(distro):
    if is_rhel(distro):
        run_command(['/usr/bin/yum', '-qy', 'install',
                     'gcc', 'make', 'patch'])
    else:
        run_command(['/usr/bin/apt-get', 'update'])
        run_command(['/usr/bin/apt-get', '-qy', 'install',
                     'gcc', 'make', 'patch'])
    shellinaboxd_file = os.path.join(USER_HOME_DIR,
                                     'shellinaboxd-install.sh')
    download_file('%s/init_files/%s/shellinaboxd-install.sh'
                  % (ATMOSERVER, SCRIPT_VERSION),
                  shellinaboxd_file,
                  match_hash='a2930f7cfe32df3d3d2e991e01cb0013d1071f15')
    run_command(['/bin/chmod', 'a+x', shellinaboxd_file])
    run_command([shellinaboxd_file], shell=True)
    run_command(['rm -rf '
                 + os.path.join(USER_HOME_DIR, 'shellinabox')
                 + '*'], shell=True)


def atmo_cl():
    download_file('%s/init_files/%s/atmocl'
                  % (ATMOSERVER, SCRIPT_VERSION),
                  '/usr/local/bin/atmocl',
                  match_hash='28cd2fd6e7fd78f1b58a6135afa283bd7ca6027a')
    download_file('%s/init_files/%s/AtmoCL.jar'
                  % (ATMOSERVER, SCRIPT_VERSION),
                  '/usr/local/bin/AtmoCL.jar',
                  match_hash='24c6acb7184c54ba666134120ac9073415a5b947')
    run_command(['/bin/chmod', 'a+x', '/usr/local/bin/atmocl'])


def nagios():
    download_file('%s/init_files/%s/nrpe-snmp-install.sh'
                  % (ATMOSERVER, SCRIPT_VERSION),
                  os.path.join(USER_HOME_DIR, 'nrpe-snmp-install.sh'),
                  match_hash='12da9f6f57c79320ebebf99b5a8516cc83c894f9')
    run_command(['/bin/chmod', 'a+x',
                 os.path.join(USER_HOME_DIR, 'nrpe-snmp-install.sh')])
    run_command([os.path.join(USER_HOME_DIR, 'nrpe-snmp-install.sh')])
    run_command(['/bin/rm',
                 os.path.join(USER_HOME_DIR, 'nrpe-snmp-install.sh')])


def notify_launched_instance(instance_data, metadata):
    try:
        import json
    except ImportError:
        # Support for python 2.4
        import simplejson as json
    service_url = instance_data['atmosphere']['instance_service_url']
    userid = instance_data['atmosphere']['userid']
    instance_token = instance_data['atmosphere']['instance_token']
    instance_name = instance_data['atmosphere']['name']
    data = {
        'action': 'instance_launched',
        'userid': userid,
        'vminfo': metadata,
        'token': instance_token,
        'name': instance_name,
    }
    data = json.dumps(data)
    request = urllib2.Request(service_url, data, {'Content-Type':
                                                  'application/json'})
    link = urllib2.urlopen(request)
    response = link.read()
    link.close()
    logging.debug(response)


def distro_files(distro):
    install_irods(distro)
    install_icommands(distro)


def is_rhel(distro):
    if 'rhel' in distro:
        return True
    else:
        return False


def install_irods(distro):
    if is_rhel(distro):
        # Rhel path
        download_file('http://www.iplantcollaborative.org/sites/default/files/'
                      + 'atmosphere/motd',
                      '/etc/motd',
                      match_hash='b8ef30b1b7d25fcaf300ecbc4ee7061e986678c4')
        download_file('http://www.iplantcollaborative.org/sites/default/files/'
                      + 'irods/irodsFs_v32.rhel5.x86_64',
                      '/usr/local/bin/irodsFs.x86_64',
                      match_hash='b286ca61aaaa16fe7a0a2a3afc209ba7bbac5128')
        run_command(['/etc/init.d/iptables', 'stop'])
        run_command(['/usr/bin/yum', '-qy',
                     'install', 'emacs', 'mosh', 'patch'])
    else:
        # Ubuntu path
        download_file('http://www.iplantcollaborative.org/sites/default/files/'
                      + 'atmosphere/motd',
                      '/etc/motd.tail',
                      match_hash='b8ef30b1b7d25fcaf300ecbc4ee7061e986678c4')
        download_file('http://www.iplantcollaborative.org/sites/default/files/'
                      + 'irods/irodsFs_v32.ubuntu12.x86_64',
                      '/usr/local/bin/irodsFs.x86_64',
                      match_hash='59b55aa0dbc44ff5b73dfc912405ff817002284f')
        run_command(['/usr/bin/apt-get', 'update'])
        run_command(['/usr/bin/apt-get', '-qy',
                     'install', 'vim', 'mosh', 'patch'])
    run_command(['/bin/chmod', 'a+x', '/usr/local/bin/irodsFs.x86_64'])


def install_icommands(distro):
    icommands_file = "icommands.x86_64.tar.bz2"
    if is_rhel(distro):
        download_file('http://www.iplantcollaborative.org/sites/default/files/'
                      + 'irods/icommands_v32.rhel5.x86_64.tar.bz2',
                      os.path.join('/opt', icommands_file),
                      match_hash='3dd3c7712ebe3548fe1e9e1f09167b5c7d925d45')
    else:
        download_file('http://www.iplantcollaborative.org/sites/default/files/'
                      + 'irods/icommands_v32.ubuntu12.x86_64.tar.bz2',
                      os.path.join('/opt', icommands_file),
                      match_hash='eb66547ed5ea159dc50f051cf399a55952b32625')

    run_command(["/bin/mkdir", "-p", "/opt/icommands/bin"])
    run_command(["/bin/tar", "--strip-components", "1", "-C",
                 "/opt/icommands/bin", "-xjf", "/opt/%s" % icommands_file])

    for f in os.listdir("/opt/icommands/bin"):
        try:
            link_f = os.path.join("/usr/local/bin", f)
            logging.debug(link_f)
            if os.path.exists(link_f):
                os.remove(link_f)
            logging.debug(os.path.join("/opt/icommands/bin", f))
            os.symlink(os.path.join("/opt/icommands/bin", f), link_f)
        except Exception:
            logging.debug(
                "Problem linking /opt/icommands/bin to /usr/local/bin")
    logging.debug("install_icommands complete.")


def update_timezone():
    run_command(['/bin/rm', '/etc/localtime'])
    run_command(
        ['/bin/ln', '-s', '/usr/share/zoneinfo/US/Arizona', '/etc/localtime'])


def run_update_sshkeys(sshdir, sshkeys):
    authorized_keys = os.path.join(sshdir, 'authorized_keys')
    f = open(authorized_keys, 'r')
    content = f.read()
    f.close()
    for key in sshkeys:
        if key in content:
            sshkeys.remove(key)
    f = open(authorized_keys, 'a')
    for key in sshkeys:
        f.write(key + '\n')
    f.close()


def update_sshkeys(metadata):
    sshkeys = [
        "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQDGjaoIl/h8IcgqK7U9i0EVYMPFad6NdgSV8gsrNLQF93+hkWEciqpX9TLn6TAcHOaL0xz7ilBetG3yaLSZBHaoKNmVCBaziHoCJ9wEwraR6Vw87iv3Lhfg/emaQiJIZF3YnPKcDDB1/He9Cnz//Y+cjQbYxLeJWdVi/irZKEWhkotb3xyfrf4o05FvLEzvaMbmf3XS1J0Rtu7BqPOvNl+U0ZqS57tNoqG2C6Cf10E340iqQGTgXzOrDmd+Rof2G1IkyKlW60okAa2N+Z8BCRB27hHY5bcS1vvnO6lo8VzWxbU3Z2MCbk1So9wHV8pAXyF1+MnVc6aJUs1xc/Lni1Xbp5USs6kOvyew3HaN3UDnoC1FSMDguAriwxho882NM/LRpGJFui2i/H3GYgQ1KQwBRqLTWEY9H8Qvy5RuOG36cy4jWJMxh6YoxOyDpZP6UlONiyuwwqrVCjUeHwIDHdBq1RGBJIEBsYhGFCYEP3UotGwEvGo7vGfb3eAebbPMsj8TAP3eR/XCd7aIeK6ES9zfNJfD2mjJqGHMUeFgbiDmTPfjGOxZ53bZssEjb0BbXNvFPezj8JetfbHZE4VUjDAUcOrLp6NT9yG6hbWFdGQxyqIbKSeMabDu8gxAcqFJvi2yFMV5j0F3qQiAPUwrigr98c4+aLvKqwsRvHxWUETBOw== idle time daemon",
        "ssh-rsa AAAAB3NzaC1yc2EAAAABIwAAAQEAvTEkREh5kmUAgx61pB0ikyH0swoXRId6yhGwIdm8KQgjErWSF8X4MED8t+7Pau98/mzxuvA23aiIn7MQWSQWQVQBFGZqj4losf+oEBS+ZQGJf2ocx3DP3NStgnixKgiDId6wjPTF1s9/YLntNb4ZNGvBSDg0bxzDJWoQ9ghOpHXmqFDWHxE9jr1qLHZzqQ0Pt1ATCW+OJ/b2staqVDPSa1SwMI89Cuw7iiSWfNHML1cf0wbYU3Bg+jT5GlwCojWP/yHqDCF1t3XL0xZQlWdKt7fM6bKUonv1CGcRZO22npZwX5Uv3U5OlskSFJnr8oZZV6V6kn99gwNzZnmiK32QQQ== edwins@iplant",
        "ssh-rsa AAAAB3NzaC1yc2EAAAABIwAAAQEAxB+KLO6pTeZ9ye/GuT2i74LBl4lvfJm7ESo4O9tNJtIf8fcAHqm9HMr2dQBixxdsLUYjVyZLZM8mZQdEtLLvdd4Fqlse74ci4RIPTgvlgwTz6dRJfABD9plTM5r5C2Rc6jLur8iVR40wbHmbgLgcilXoYnRny4bFoAhfAHt2vxiMY6wnhiL9ESSUA/i1LrcYcGj2QAvAPLf2yTJFtXSCwnlBIJBjMASQiPaIU2+xUyQisgSF99tBS3DZyu4NVGnSGYGmKl84CEFp+x57US4YAl9zuAnM9ckTp4mOjStEvIpyyPJA03tDbfObSi50Qh5zta9I1PIAGxOznT6dJbI1bw== aedmonds@iplant",
        "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDgvgRtXgkvM/+eCSEqVuTiUpZMjRfA9AnXfz0YWS93uKImoodE5oJ7wUZqjpOmgXyX0xUDI4O4bCGiWVmSyiRiQpqZrRrF7Lzs4j0Nf6WvbKblPQMwcmhMJuaI9CwU5aEbEqkV5DhBHcUe4bFEb28rOXuUW6WMLzr4GrdGUMd3Fex64Bmn3FU7s6Av0orsgzVHKmoaCbqK2t3ioGAt1ISmeJwH6GasxmrSOsLLW+L5F65WrYFe0AhvxMsRLKQsuAbGDtFclOzrOmBudKEBLkvwkblW8PKg06hOv9axNX7C9xlalzEFnlqNWSJDu1DzIa2NuOr8paW5jgKeM78yuywt jmatt@leia",
        "ssh-rsa AAAAB3NzaC1yc2EAAAABIwAAAQEA2TtX9DohsBaOEoLlm8MN+W+gVp40jyv752NbMP/PV/LAz5MnScJcvbResAJx2AusL1F6sRNvo9poNZiab6wpfErQPZLfKGanPZGYSdonsNAhTu/XI+4ERPQXUA/maQ2qZtL1b+bmZxg9n/5MsZFpA1HrXP3M2LzYafF2IzZYWfsPuuZPsO3m/cUi0G8n7n0IKXZ4XghjGP5y/kmh5Udy9I5qreaTvvFlNJtBE9OL39EfWtjOxNGllwlGIAdsljfRxkeOzlahgtCJcaoW7X2A7GcV52itUwMKfTIboAXnZriwh5n0o1aLHCCdUAGDGHBYmP7fO7/2gIQKgpLfRkDEiQ== sangeeta@iplant",
        "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC+SYMny6H2B5IjXe6gxofHRNza5LE3NqTCe6YgYnnzYjyXWtopSeb8mK2q1ODzlaQyqYoTvPqtn6rSyN+5oHGV4o6yU+Fl664t5rOdAwz/jGJK3WwG60Pc0eGQco0ldgjD7K6LWYVPIJZs+rGpZ70jF5JsTuHeplXOn5MX9oUvNxxgXRuySxvBNOGMn0RxydK8tBTbZMlJ5MkAi/bIOrEDHEfejCxKGWITpXGkdTS2s4THiY8WqFdHUPtQkEfQkXCsRpZ6HPw1gN+JYD5NI38dVVmrA+3MgFVJkwtLUbbAM0yxgKwaUaipNN1+DeYOxBuVRlRwrrAp3+fq+4QCJrXd root@dalloway",
        "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDFE/lyzLdFYZF3mxYwzrTITgov1NqtLuS5IY0fgjpdiVpHjWBUdXspTafKORbbM+t0ERTOqcSt24Vj5B8XUXImpzw2OAsl//AiKvHGRUenk7qY6/9IEUcay5mGAoiRpjLzDIDdtiQUAAEMKvkzanUBQOBJWVyO4Gq2aFUr4zweVLfvjejOspf2cZll/ojcPYmI9cKMq7fOgKSmRH2zUg+ORFlP1rQYugoETcGkcQg0IBsSMLT8gnYt3UWTW8S8ugtb4aaWVrId14Nc3sk+yDzPBaRX7iM3CQ5uKXPwjeID59RLMjQUFlHjqDSdZBOjXCFRHZbrbZZjS42o4OJAoLvF sgregory@mickey",
        "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDQNBua13LVIG61LNztP9b7k7T+Qg8t22Drhpy17WVwbBH1CPYdn5NR2rXUmfiOa3RhC5Pz6uXsYUJ4xexOUJaFKY3S8h9VaeaPxMyeA8oj9ssZC6tNLqNxqGzKJbHfSzQXofKwBH87e+du34mzqzm2apOMT2JVzxWmTwrl3JWnd2HG0odeVKMNsXLuQFN6jzCeJdLxHpu+dJOL6gJTW5t9AwoJ8jxmwO8xgUbk+7s38VATSuaV/RiIfXfGFv34CT7AY1gRxm1og9jjP6qkFMyZiO6M+lwrJIlHKTOKxw+xc15w/tIssUkeflzAcrkkNGzT8sBL39BoQOo9RTrMD2QL weather-balloon@wesley.iplantcollaborative.org",
        "ssh-rsa AAAAB3NzaC1yc2EAAAABIwAAAQEAo/O1gw1hn7I8sDgKGsIY/704O4/89JFO2AG2Quy9LCS5dO5HL40igFOUBmVkqy9ANPEMslaA5VwzPuP+ojKmDhTzoWc4wmvnCGjnZqaTW/+M+QfPSOKoyAaevKC4/Y2dxevS7eRdbeY5Pvweu5rf/eoCXF4DnGMWJ4C6IPVHy7gYpfZrdeiaYzxus53DvFNr4Dee9Y2jvY8wuS3EvL37DU1AGsv1UAN2IoOKZ9Itxwmhf/ZfnFyqMdebggceWRmpK/U2FuXewKMjoJ+HMWgzESR2Rit+9jGniiIVV3K5JeNmHqfWxu2BLpXDYEalX6l28opaiEbDevirwWmvoaAbDw== dboss"]
    more_keys = get_metadata_keys(metadata)
    sshkeys.extend(more_keys)
    root_ssh_dir = '/root/.ssh'
    mkdir_p(root_ssh_dir)
    run_update_sshkeys(root_ssh_dir, sshkeys)
    global USER_HOME_DIR
    if USER_HOME_DIR != '/root':
        home_ssh_dir = os.path.join(USER_HOME_DIR, '.ssh')
        mkdir_p(home_ssh_dir)
        run_update_sshkeys(home_ssh_dir, sshkeys)


def set_user_home_dir():
    global USER_HOME_DIR
    USER_HOME_DIR = os.path.expanduser("~")
    if not USER_HOME_DIR:
        USER_HOME_DIR = '/root'
    logging.debug("User home directory - %s" % USER_HOME_DIR)


def denyhost_whitelist():
    allow_list = [
        "127.0.0.1"
        "128.196.38.[1-127]"
        "128.196.64.[1-512]"
        "128.196.142.*"
        "128.196.172.[128-255]"
        "150.135.78.*"
        "150.135.93.[128-255]"
        "10.130.5.[128-155]"
        "10.140.65.*"
    ]
    filename = "/var/lib/denyhosts/allowed-hosts"
    dirname = os.path.dirname(filename)
    if not os.path.exists(dirname):
        mkdir_p(dirname)
    if os.path.exists(filename):
        logging.error("Removing existing file: %s" % filename)
        os.remove(filename)
    allowed_hosts_content = "\n".join(allow_list)
    # Don't write if the folder doesn't exist
    if os.path.exists("/var/lib/denyhosts"):
        write_to_file(filename, allowed_hosts_content)
    return


def update_sudoers():
    run_command(['/bin/sed', '-i',
                 "s/^Defaults    requiretty/#Defaults    requiretty/",
                 '/etc/sudoers'])


def ldap_replace():
    run_command(['/bin/sed', '-i',
                 "s/128.196.124.23/ldap.iplantcollaborative.org/",
                 '/etc/ldap.conf'])


def ldap_install():
    # package install
    ldap_replace()


def insert_modprobe():
    run_command(['depmod', '-a'])
    run_command(['modprobe', 'acpiphp'])


def main(argv):
    init_logs('/var/log/atmo/atmo_init_full.log')
    instance_data = {"atmosphere": {}}
    service_type = None
    instance_service_url = None
    instance_service_url = None
    server = None
    root_password = None
    user_id = None
    vnclicense = None
    try:
        opts, args = getopt.getopt(
            argv,
            "t:u:s:i:T:N:v:",
            ["service_type=", "service_url=", "server=", "user_id=", "token=",
             "name=", "vnc_license=", "root_password="])
    except getopt.GetoptError:
        logging.error("Invalid arguments provided.")
        sys.exit(2)
    for opt, arg in opts:
        if opt in ("-t", "--service_type"):
            instance_data["atmosphere"]["service_type"] = arg
            service_type = arg
        elif opt in ("-T", "--token"):
            instance_data["atmosphere"]["instance_token"] = arg
            instance_token = arg
        elif opt in ("-N", "--name"):
            instance_data["atmosphere"]["name"] = arg
            instance_token = arg
        elif opt in ("-u", "--service_url"):
            instance_data["atmosphere"]["instance_service_url"] = arg
            instance_service_url = arg
        elif opt in ("-s", "--server"):
            instance_data["atmosphere"]["server"] = arg
            global ATMOSERVER
            ATMOSERVER = arg
            server = arg
        elif opt in ("-i", "--user_id"):
            instance_data["atmosphere"]["userid"] = arg
            user_id = arg
        elif opt in ("-v", "--vnc_license"):
            vnclicense = arg
        elif opt in ("--root_password"):
            root_password = arg
        elif opt == '-d':
            global _debug
            _debug = 1
            logging.setLevel(logging.DEBUG)

    # TODO: What is this line for?
    source = "".join(args)
    logging.debug("Atmoserver - %s" % ATMOSERVER)
    logging.debug("Atmosphere init parameters- %s" % instance_data)
    set_user_home_dir()
    instance_metadata = get_metadata()
    logging.debug("Instance metadata - %s" % instance_metadata)
    distro = get_distro()
    logging.debug("Distro - %s" % distro)

    linuxuser = instance_data['atmosphere']['userid']
    linuxpass = ""
    public_ip = get_public_ip(instance_metadata)
    hostname = get_hostname(instance_metadata)
    set_hostname(hostname, distro)
    instance_metadata['linuxusername'] = linuxuser
    instance_metadata["linuxuserpassword"] = linuxpass
    instance_metadata["linuxuservncpassword"] = linuxpass

    # TODO: Test this is multi-call safe
    update_sshkeys(instance_metadata)
    update_sudoers()

    if not in_sudoers(linuxuser):
        add_sudoers(linuxuser)
    if not in_etc_group('/etc/group', linuxuser):
        add_etc_group(linuxuser)
    # is_updated_test determines if this sensitive file needs
    if not is_updated_test("/etc/ssh/sshd_config"):
        ssh_config(distro)
    if root_password:
        set_root_password(root_password, distro)

    if not is_rhel(distro):
        run_command(['/usr/bin/apt-get', 'update'])

    mount_storage()
    ldap_install()
    etc_skel_bashrc(linuxuser)
    run_command(['/bin/cp', '-rp',
                 '/etc/skel/.',
                 '/home/%s' % linuxuser])
    run_command(['/bin/chown', '-R',
                 '%s:iplant-everyone' % (linuxuser,),
                 '/home/%s' % linuxuser])
    run_command(['/bin/chmod', 'a+rwxt', '/tmp'])
    run_command(['/bin/chmod', 'a+rx', '/bin/fusermount'])
    run_command(['/bin/chmod', 'u+s', '/bin/fusermount'])
    vnc(linuxuser, distro, vnclicense)
    iplant_files(distro)
    nagios()
    distro_files(distro)
    update_timezone()
    shellinaboxd(distro)
    insert_modprobe()
    denyhost_whitelist()
    modify_rclocal(linuxuser, distro, hostname)
    notify_launched_instance(instance_data, instance_metadata)
    logging.info("Complete.")


if __name__ == "__main__":
    main(sys.argv[1:])
