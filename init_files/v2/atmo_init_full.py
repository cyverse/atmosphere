#!/usr/bin/env python
"""
Debugging atmo_init_full locally:
    cd /usr/sbin
    touch __init__.py
    python
    >>> import atmo_init_full
    >>>
"""
import errno
import getopt
import glob
try:
    from hashlib import sha1
except ImportError:
    # Support for python 2.4
    from sha import sha as sha1
try:
    import json
except ImportError:
    import simplejson as json
import logging
import os
import re
import shutil
import subprocess
import sys
import time
import urllib2
import pwd


ATMOSERVER = ""
ATMO_INIT_FILES = ""
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


def download_file(url, fileLoc, retry=True, match_hash=None):
    waitTime = 0
    attempts = 0
    max_attempts = 20
    contents = None
    while True:
        attempts += 1
        logging.debug(
            'Download File:%s Attempt: %s, Wait %s seconds' %
            (url, attempts, waitTime))
        time.sleep(waitTime)
        # Exponential backoff * 10s = 20s,40s,80s,160s,320s...
        waitTime = max(10 * 2**attempts, 120)
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
        if attempts >= max_attempts:
            logging.debug(
                "File could NOT be downloaded: %s Download attempted %s times." %
                (url, max_attempts))
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
        if os.path.exists("/etc/dhcp"):
            download_file(
                '%s/%s/hostname-exit-hook.sh'
                % (ATMO_INIT_FILES, SCRIPT_VERSION),
                "/etc/dhcp/dhclient-exit-hooks",
                match_hash='')
            run_command(['/bin/chmod', 'a+x', "/etc/dhcp/dhclient-exit-hooks"])
        else:
            download_file(
                '%s/%s/hostname-exit-hook.sh'
                % (ATMO_INIT_FILES, SCRIPT_VERSION),
                "/etc/dhclient-exit-hooks",
                match_hash='')
            run_command(['/bin/chmod', 'a+x', "/etc/dhclient-exit-hooks"])
    else:
        download_file(
            '%s/%s/hostname-exit-hook.sh'
            % (ATMO_INIT_FILES, SCRIPT_VERSION),
            "/etc/dhcp/dhclient-exit-hooks.d/hostname",
            match_hash='')
        run_command(
            ['/bin/chmod', 'a+x', "/etc/dhcp/dhclient-exit-hooks.d/hostname"])


def _get_local_ip():
    try:
        import socket
    except ImportError:
        logging.warn("Socket module does not exist!")
        return None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Google DNS availability
        s.connect(("8.8.8.8", 80))
        ip_addr = s.getsockname()[0]
        s.close()
        return ip_addr
    except socket.gaierror:
        return None


def _test_hostname(hostname):
    try:
        import socket
    except ImportError:
        logging.warn("Socket module does not exist!")
        return False
    try:
        socket.gethostbyname_ex(hostname)
        return True
    except socket.gaierror:
        return False


def _get_hostname_by_socket(public_ip):
    try:
        import socket
    except ImportError:
        logging.warn("Socket module does not exist!")
        return public_ip
    fqdn = socket.getfqdn(public_ip)
    return fqdn

# this is necessary because tacc ips do not have a reverse lookup


def tacc_ip2hostname(ip):

    # let's split the ip first
    octets = ip.split(".")

    # simple check to verify ip number and last octet
    if ip.startswith("129.114.5.") and octets[3].isdigit():
        return "austin5-" + octets[3] + ".cloud.bio.ci"
    else:
        return None


def get_hostname(instance_metadata, public_ip_hint=None):
    """
    Attempts multiple ways to establish the public IP and hostname.
    The hostname will be tested for DNS resolution before it is applied
    (To avoid setting <machine_name>.novalocal)
    """
    ip_address = None
    # 1. Look for 'public-ipv4' in metadata
    if not instance_metadata:
        instance_metadata = {}
    if 'public-ipv4' in instance_metadata:
        public_hostname = tacc_ip2hostname(instance_metadata['public-ipv4'])
        if not public_hostname:
            public_hostname = _get_hostname_by_socket(
                instance_metadata['public-ipv4'])
        result = _test_hostname(public_hostname)
        if result:
            return public_hostname

    # 2. Look in user-defined metadata public-hostname OR public-ip
    defined_metadata = instance_metadata.get('meta', {})
    if defined_metadata.get('public-hostname'):
        public_hostname = defined_metadata['public-hostname']
        result = _test_hostname(public_hostname)
        if result:
            return public_hostname
    if defined_metadata.get('public-ip'):
        public_hostname = tacc_ip2hostname(defined_metadata['public-ip'])
        if not public_hostname:
            public_hostname = _get_hostname_by_socket(
                defined_metadata['public-ip'])
        result = _test_hostname(public_hostname)
        if result:
            return public_hostname
    if public_ip_hint:
        public_hostname = tacc_ip2hostname(public_ip_hint)
        if not public_hostname:
            public_hostname = _get_hostname_by_socket(public_ip_hint)
        result = _test_hostname(public_hostname)
        if result:
            return public_hostname
    # 4. As a last resort, use the instance's (Fixed) IP address
    ip_addr = _get_local_ip()
    if ip_addr:
        return ip_addr
    # 5. If NONE of these work, use 'localhost'
    return 'localhost'


def get_public_ip(instance_metadata):
    """
    Checks multiple locations in metadata for the IP address
    """
    ip_addr = instance_metadata.get('public-ipv4')
    if not ip_addr:
        defined_metadata = instance_metadata.get('meta', {})
        if defined_metadata.get('public-ip'):
            ip_addr = defined_metadata['public-ip']
            logging.info("NOTE: key 'public-ipv4' MISSING from metadata!"
                         " Falling back to defined metadata:%s" % ip_addr)
            return
    if not ip_addr:
        ip_addr = instance_metadata.get('local-ipv4')
    if not ip_addr:
        ip_addr = _get_local_ip()
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
    etc_group_contents = read_file(filename)
    for line in etc_group_contents.split('\n'):
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


def etc_skel_bashrc(user):
    filename = "/etc/skel/.bashrc"
    if not is_updated_test(filename):
        # TODO: Should this be $USER instead of %s?
        append_to_file(filename, """
export IDS_HOME="/irods/data.iplantc.org/iplant/home/%s"
alias ids_home="cd $IDS_HOME"
""" % user)


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
    os_key = _make_request('%s%s' % (openstack_meta_server,
                                     "public-keys/0/openssh-key/"))
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
    metadata = collect_metadata(openstack_meta_server)
    metadata.update(collect_json_metadata(openstack_json_metadata))
    return metadata


def collect_json_metadata(metadata_url):
    content = _make_request(metadata_url)
    try:
        meta_obj = json.loads(content)
    except ValueError as bad_content:
        logging.exception("JSON Metadata not found. url: %s" % metadata_url)
        meta_obj = {}

    return meta_obj


def _make_request(request_url):
    try:
        logging.info("Making request to %s" % request_url)
        resp = urllib2.urlopen(request_url)
        content = resp.read()
        return content
    except Exception as e:
        logging.exception("Could not retrieve meta-data for instance")
        return ""


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
            if not match:
                continue
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


def start_vncserver(user):
    if not running_process("vncserver", user):
        run_command(['/bin/su', '%s' % user, '-c', '/usr/bin/vncserver'])


def running_process(proc_name, user=None):
    if user:
        logging.debug("Limiting scope of Process %s to those launched by %s"
                      % (proc_name, user))
        pgrep_str = "pgrep -u %s %s" % (user, proc_name)
    else:
        pgrep_str = "pgrep %s" % proc_name
    out, err = run_command([pgrep_str], shell=True)
    # Output if running:
    # 4444
    # 4445  (The Running PIDs)
    # Output if not running:
    if len(out) > 1:
        logging.debug("Found PID(s) %s for proccess name:%s"
                      % (out, proc_name))
        return True
    logging.debug("No PID found for proccess name:%s" % (proc_name))
    return False


def vnc(user, distro, license=None):
    try:
        if not os.path.isfile('/usr/bin/X')\
           and not os.path.isfile('/usr/bin/xterm'):
            logging.debug("Could not find a GUI on this machine, "
                          "Skipping VNC Install.")
            return
        # ASSERT: VNC server installed on this machine
        if is_rhel(distro):
            run_command(['/usr/bin/yum', '-qy', 'remove', 'vnc-E',
                         'realvnc-vnc-server'])
            download_file(
                '%s/%s/VNC-Server-5.2.3-Linux-x64.rpm'
                % (ATMO_INIT_FILES, SCRIPT_VERSION),
                "/opt/VNC-Server-5.2.3-Linux-x64.rpm",
                match_hash='3cbae24319b3cfb63065e94756a7caf0a5d33a7f')
            run_command(['/bin/rpm', '-Uvh',
                         '/opt/VNC-Server-5.2.3-Linux-x64.rpm'])
            run_command(['/bin/sed', '-i',
                         "'$a account    include      system-auth'",
                         '/etc/pam.d/vncserver.custom'], bash_wrap=True)
            run_command(['/bin/sed', '-i',
                         "'$a password   include      system-auth'",
                         '/etc/pam.d/vncserver.custom'], bash_wrap=True)
        else:
            download_file(
                '%s/%s/VNC-Server-5.2.3-Linux-x64.deb'
                % (ATMO_INIT_FILES, SCRIPT_VERSION),
                "/opt/VNC-Server-5.2.3-Linux-x64.deb",
                match_hash='4d29304e6178064a636414a64fdb938079431422')
            run_command(['/usr/bin/dpkg', '-i',
                         '/opt/VNC-Server-5.2.3-Linux-x64.deb'])
            new_file = open('/etc/pam.d/vncserver.custom', 'w')
            new_file.write("auth include  common-auth")
            new_file.close()
            new_file = open('/etc/vnc/config.d/common.custom', 'w')
            new_file.write("PamApplicationName=vncserver.custom")
            new_file.close()
        time.sleep(1)
        run_command(['/usr/bin/vnclicense', '-add', license], block_log=True)
        download_file(
            '%s/%s/vnc-config.sh'
            % (ATMO_INIT_FILES, SCRIPT_VERSION),
            os.path.join(USER_HOME_DIR, 'vnc-config.sh'),
            match_hash='95f9095c443b80f912571308f7b4104005597456')
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
        start_vncserver(user)
    except Exception as e:
        logging.exception('Failed to install VNC')


def parrot_install(distro):
    try:
        run_command(['rm -rf '
                 + os.path.join('/opt', 'cctools')
                 + '*'], shell=True)
        cctools = 'cctools-5.0.3-x86_64-redhat5'
        cctools_file = '%s.tar.gz' % cctools
        download_file(
            'http://www.iplantcollaborative.org/sites/default/files'
            + '/atmosphere/cctools/%s' % (cctools_file),
            '/opt/%s' % (cctools_file),
            match_hash='9008a1b2fea74b49809013cd804c4e96c4d50d22')
        run_command(
            ['/bin/tar', 'zxf',
             '/opt/%s' % (cctools_file),
             '-C', '/opt/'])
        run_command(
            ['/bin/ln', '-s',
             '/opt/%s' % (cctools),
             '/opt/cctools'])
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

    download_file('%s/%s/iplant_backup.sh'
                  % (ATMO_INIT_FILES, SCRIPT_VERSION),
                  "/usr/local/bin/iplant_backup",
                  match_hash='72925d4da5ed30698c81cc95b0a610c8754500e7')
    run_command(['/bin/chmod', 'a+x', "/usr/local/bin/iplant_backup"])


def idrop(username, distro):
    download_file("%s/%s/iDrop201RC1-008.tgz" % (ATMO_INIT_FILES, SCRIPT_VERSION),
                  "/opt/iDrop201RC1-008.tgz",
                  match_hash="79abcaebd00a3090d926a6a8599305506616a00f")
    download_file(
        "%s/%s/idrop.desktop" % (ATMO_INIT_FILES, SCRIPT_VERSION),
        "/opt/idrop.desktop",
        match_hash="c0dbe48b733478549d3d1eb4ad4468861bcbd3bd")
    run_command(["/bin/tar", "-xvzf", "/opt/iDrop201RC1-008.tgz", "-C", "/opt/"])
    new_idropdesktop = "/opt/idrop.desktop"
    if not os.path.isdir("/etc/skel/Desktop"):
        os.makedirs("/etc/skel/Desktop")
    if os.path.exists("/etc/skel/Desktop/idrop.desktop"):
        os.remove("/etc/skel/Desktop/idrop.desktop")
    shutil.copy2(new_idropdesktop, "/etc/skel/Desktop/idrop.desktop")
    for name in os.listdir("/home/"):
        dirname = os.path.join("/home/", name)
        if os.path.isdir(dirname):
            if not os.path.exists(os.path.join(dirname, "Desktop")):
                continue
            idrop_path = os.path.join(dirname, "Desktop/")
            idrop_match_str = os.path.join(
                idrop_path,
                "[i,I][d,D][r,R][o,O][p,P].desktop")
            idrop_files = glob.glob(idrop_match_str)
            for idrop_file in idrop_files:
                if os.path.exists(idrop_file):
                    os.remove(idrop_file)
            shutil.copy2(new_idropdesktop, idrop_path)
    os.remove("/opt/iDrop201RC1-008.tgz")
    os.remove("/opt/idrop.desktop")
    shutil.rmtree("/opt/irodsidrop", ignore_errors=True)


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
                           # Add new rc.local commands here
                           # And they will be excecuted on startup
                           # Don't forget the newline char
                           % (hostname))
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
    download_file('%s/%s/shellinaboxd-install.sh'
                  % (ATMO_INIT_FILES, SCRIPT_VERSION),
                  shellinaboxd_file,
                  match_hash='1e057ca1ac9986cb829d5c138d4f7d9532dcab12')
    run_command(['/bin/chmod', 'a+x', shellinaboxd_file])
    run_command([shellinaboxd_file], shell=True)
    run_command(['rm -rf '
                 + os.path.join(USER_HOME_DIR, 'shellinabox')
                 + '*'], shell=True)
    start_shellinaboxd()


def start_shellinaboxd():
    if not running_process("shellinaboxd"):
        run_command([
            "/usr/bin/nohup /usr/local/bin/shellinaboxd -b -t "
            "-f beep.wav:/dev/null > /var/log/atmo/shellinaboxd.log 2>&1 &"],
            shell=True)


def atmo_cl():
    download_file('%s/%s/atmocl'
                  % (ATMO_INIT_FILES, SCRIPT_VERSION),
                  '/usr/local/bin/atmocl',
                  match_hash='28cd2fd6e7fd78f1b58a6135afa283bd7ca6027a')
    download_file('%s/%s/AtmoCL.jar'
                  % (ATMO_INIT_FILES, SCRIPT_VERSION),
                  '/usr/local/bin/AtmoCL.jar',
                  match_hash='24c6acb7184c54ba666134120ac9073415a5b947')
    run_command(['/bin/chmod', 'a+x', '/usr/local/bin/atmocl'])


def nagios():
    download_file('%s/%s/nrpe-snmp-install.sh'
                  % (ATMO_INIT_FILES, SCRIPT_VERSION),
                  os.path.join(USER_HOME_DIR, 'nrpe-snmp-install.sh'),
                  match_hash='9076213c0c53d18dbfcb26dfe95e7650256b54da')
    run_command(['/bin/chmod', 'a+x',
                 os.path.join(USER_HOME_DIR, 'nrpe-snmp-install.sh')])
    run_command([os.path.join(USER_HOME_DIR, 'nrpe-snmp-install.sh')])
    run_command(['/bin/rm',
                 os.path.join(USER_HOME_DIR, 'nrpe-snmp-install.sh')])


def distro_files(distro):
    install_motd(distro)
    try:
        install_irods(distro)
    except IOError as file_busy_err:
        pass
    install_icommands(distro)


def is_rhel(distro):
    if 'rhel' in distro:
        return True
    else:
        return False


def install_motd(distro):
    if is_rhel(distro):
        # Rhel path
        download_file('http://www.iplantcollaborative.org/sites/default/files/'
                      + 'atmosphere/motd',
                      '/etc/motd',
                      match_hash='b8ef30b1b7d25fcaf300ecbc4ee7061e986678c4')
    else:
        # Ubuntu path
        download_file('http://www.iplantcollaborative.org/sites/default/files/'
                      + 'atmosphere/motd',
                      '/etc/motd.tail',
                      match_hash='b8ef30b1b7d25fcaf300ecbc4ee7061e986678c4')
    include_motd_more(distro)


def include_motd_more(distro):
    if not os.path.exists("/etc/motd.more"):
        return
    motd_message = read_file("/etc/motd.more")
    if is_rhel(distro):
        filename = "/etc/motd"
    else:
        filename = "/etc/motd.tail"
    append_to_file(filename, "\n---\n%s" % motd_message)


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
                      + 'irods/icommands_v331.centos.x86_64.tar.bz2',
                      os.path.join('/opt', icommands_file),
                      match_hash='78c88999c10331076b2cff3596926968bdd6545b')
    else:
        download_file('http://www.iplantcollaborative.org/sites/default/files/'
                      + 'irods/icommands_v331.ubuntu.x86_64.tar.bz2',
                      os.path.join('/opt', icommands_file),
                      match_hash='de8a1749c6bbda883b1bae515a56f42cf00dacdf')

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
    included_ssh_keys = read_file(authorized_keys)
    for key in sshkeys:
        if key in included_ssh_keys:
            sshkeys.remove(key)
    f = open(authorized_keys, 'a')
    for key in sshkeys:
        f.write(key + '\n')
    f.close()


def update_sshkeys(metadata):
    sshkeys = [
        "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQDGjaoIl/h8IcgqK7U9i0EVYMPFad6NdgSV8gsrNLQF93+hkWEciqpX9TLn6TAcHOaL0xz7ilBetG3yaLSZBHaoKNmVCBaziHoCJ9wEwraR6Vw87iv3Lhfg/emaQiJIZF3YnPKcDDB1/He9Cnz//Y+cjQbYxLeJWdVi/irZKEWhkotb3xyfrf4o05FvLEzvaMbmf3XS1J0Rtu7BqPOvNl+U0ZqS57tNoqG2C6Cf10E340iqQGTgXzOrDmd+Rof2G1IkyKlW60okAa2N+Z8BCRB27hHY5bcS1vvnO6lo8VzWxbU3Z2MCbk1So9wHV8pAXyF1+MnVc6aJUs1xc/Lni1Xbp5USs6kOvyew3HaN3UDnoC1FSMDguAriwxho882NM/LRpGJFui2i/H3GYgQ1KQwBRqLTWEY9H8Qvy5RuOG36cy4jWJMxh6YoxOyDpZP6UlONiyuwwqrVCjUeHwIDHdBq1RGBJIEBsYhGFCYEP3UotGwEvGo7vGfb3eAebbPMsj8TAP3eR/XCd7aIeK6ES9zfNJfD2mjJqGHMUeFgbiDmTPfjGOxZ53bZssEjb0BbXNvFPezj8JetfbHZE4VUjDAUcOrLp6NT9yG6hbWFdGQxyqIbKSeMabDu8gxAcqFJvi2yFMV5j0F3qQiAPUwrigr98c4+aLvKqwsRvHxWUETBOw== idle time daemon",
        "ssh-rsa AAAAB3NzaC1yc2EAAAABIwAAAQEAvTEkREh5kmUAgx61pB0ikyH0swoXRId6yhGwIdm8KQgjErWSF8X4MED8t+7Pau98/mzxuvA23aiIn7MQWSQWQVQBFGZqj4losf+oEBS+ZQGJf2ocx3DP3NStgnixKgiDId6wjPTF1s9/YLntNb4ZNGvBSDg0bxzDJWoQ9ghOpHXmqFDWHxE9jr1qLHZzqQ0Pt1ATCW+OJ/b2staqVDPSa1SwMI89Cuw7iiSWfNHML1cf0wbYU3Bg+jT5GlwCojWP/yHqDCF1t3XL0xZQlWdKt7fM6bKUonv1CGcRZO22npZwX5Uv3U5OlskSFJnr8oZZV6V6kn99gwNzZnmiK32QQQ== edwins@iplant",
        "ssh-rsa AAAAB3NzaC1yc2EAAAABIwAAAQEAyKSEZEFIZw9IaJAzSVM0qCfyDunTandlvLFq/VR/uyMvCRvpZC1RxwZ5BjQPNA5ARAcH54v7Mx3/W2616h5qDcyrQrXVl2pulQUMiq/YeNBQMhYEt+AGn38gsBrsRjH9bdHkpugTtuM6LyYhLwVDk8cM+xNshKT8IdAIyZQA5iBYeUiQaDsKVfRH9Tl+muA3One3ASzKKwySePB5SFydeDxWJoYJktBAaR0C5sab1DIFOHmkQBHOuBkIKeRqkwx0BbbyJORRMYDIGazTMhyF6F3hEtrDKDc6wy72e45BKh4VHeaJCGfwiyODA+le4RBgrVN7srRvMlWZDeSiNraF3w== edwin@acat.iplantcollaborative.org",
        "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQD34d6kx8MNcJzxNu04xzv+d85MF6orj7m3d7XYuYixZJSg2osgXXsGthgwupB3jQz894PK3fADurvWGjEpfJ0VBVMjcH2YZtdGJvjs7jPSAo0cbjFXT5C4+CmsVEAfPuzU28I465ltiMt8AywkDMYNUIAZ9Ckbxub5qT7BMj0bYGcGW1OCDkhBB75SqceO891/chbSkmyx/SS3Ngr2Hnb0tnzfkiaUqSvXf54wV7v/Re4hr0B96qUcUmVwfsJUb0lCiVznlBTDeyOXvJ6Hi4ouDxcfVhxZHwEJ4U8jfJ9CCEVRCFvVwKskV8eQZ1UqWXPs75Wl8UPhdWbemZpRs8+aUFrTJi6q3bdtlot3ll1ysDdLYgQo7qv/R/+Wa9b3/Ujuvv3Qaf4GebdSQHXhJ0NVOg+f0Kp0t36QXpKjQCL8RKvXX/D8OII9OK62Vt4yNB4QfkibjI96T2A5vUAaWuVmC8qpndN7swEo4y9dXxMvHprJXbVGdE2hS7cS/R5wOjscuURCw5k4vsbo3ifTu77OMApxB+AyiSBEtMkxQ3mT3rS6/zF8wLWYt/kSuwuyTt1wWEXIr9vjaBMuONsb1OxDYfG8bCQ9peZQyWCqpwLix7akP2lDuoDQSfjtynguXFByiP3AojTiZF9xhhACuNKyhgD+lzCsCmyEYiO5uTbzaQ== edwin@rose",
        "ssh-rsa AAAAB3NzaC1yc2EAAAABIwAAAQEAxB+KLO6pTeZ9ye/GuT2i74LBl4lvfJm7ESo4O9tNJtIf8fcAHqm9HMr2dQBixxdsLUYjVyZLZM8mZQdEtLLvdd4Fqlse74ci4RIPTgvlgwTz6dRJfABD9plTM5r5C2Rc6jLur8iVR40wbHmbgLgcilXoYnRny4bFoAhfAHt2vxiMY6wnhiL9ESSUA/i1LrcYcGj2QAvAPLf2yTJFtXSCwnlBIJBjMASQiPaIU2+xUyQisgSF99tBS3DZyu4NVGnSGYGmKl84CEFp+x57US4YAl9zuAnM9ckTp4mOjStEvIpyyPJA03tDbfObSi50Qh5zta9I1PIAGxOznT6dJbI1bw== aedmonds@iplant",
        "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDgvgRtXgkvM/+eCSEqVuTiUpZMjRfA9AnXfz0YWS93uKImoodE5oJ7wUZqjpOmgXyX0xUDI4O4bCGiWVmSyiRiQpqZrRrF7Lzs4j0Nf6WvbKblPQMwcmhMJuaI9CwU5aEbEqkV5DhBHcUe4bFEb28rOXuUW6WMLzr4GrdGUMd3Fex64Bmn3FU7s6Av0orsgzVHKmoaCbqK2t3ioGAt1ISmeJwH6GasxmrSOsLLW+L5F65WrYFe0AhvxMsRLKQsuAbGDtFclOzrOmBudKEBLkvwkblW8PKg06hOv9axNX7C9xlalzEFnlqNWSJDu1DzIa2NuOr8paW5jgKeM78yuywt jmatt@leia",
        "ssh-rsa AAAAB3NzaC1yc2EAAAABIwAAAQEA2TtX9DohsBaOEoLlm8MN+W+gVp40jyv752NbMP/PV/LAz5MnScJcvbResAJx2AusL1F6sRNvo9poNZiab6wpfErQPZLfKGanPZGYSdonsNAhTu/XI+4ERPQXUA/maQ2qZtL1b+bmZxg9n/5MsZFpA1HrXP3M2LzYafF2IzZYWfsPuuZPsO3m/cUi0G8n7n0IKXZ4XghjGP5y/kmh5Udy9I5qreaTvvFlNJtBE9OL39EfWtjOxNGllwlGIAdsljfRxkeOzlahgtCJcaoW7X2A7GcV52itUwMKfTIboAXnZriwh5n0o1aLHCCdUAGDGHBYmP7fO7/2gIQKgpLfRkDEiQ== sangeeta@iplant",
        "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCZl557abm+BvoEn6WMpUJYZV+TWe1Gc3ApQbMcf+3kItRhDBvbe5hTijiex7HFnxqRGkMkzpr2vazNrGO1SFXbqGnXOeoxkJKFAslr/+9o8uKo4XO+Hq35cuJ99Wm4E6tIgzEN5sMPkUfD8YY7IOuii4covKSDXrBiCcLoxjbb8ViH2BFaeaMQhiLV8/GqzKYOZYWkVkdew1CcvGRJGF0dFE7ibwNp+M8La/r3//mJp9+foksei2BxL4mQp22w1Z0FvLeV70iQ09vJO5NN2T9RJH/hhtYNZfrXRjEG+trJNvLktj2h3WxcDHRlB9vnEKAykT2LSblDPTMhRl4d0Lff root@dalloway",
        "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDFE/lyzLdFYZF3mxYwzrTITgov1NqtLuS5IY0fgjpdiVpHjWBUdXspTafKORbbM+t0ERTOqcSt24Vj5B8XUXImpzw2OAsl//AiKvHGRUenk7qY6/9IEUcay5mGAoiRpjLzDIDdtiQUAAEMKvkzanUBQOBJWVyO4Gq2aFUr4zweVLfvjejOspf2cZll/ojcPYmI9cKMq7fOgKSmRH2zUg+ORFlP1rQYugoETcGkcQg0IBsSMLT8gnYt3UWTW8S8ugtb4aaWVrId14Nc3sk+yDzPBaRX7iM3CQ5uKXPwjeID59RLMjQUFlHjqDSdZBOjXCFRHZbrbZZjS42o4OJAoLvF sgregory@mickey",
        "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDQNBua13LVIG61LNztP9b7k7T+Qg8t22Drhpy17WVwbBH1CPYdn5NR2rXUmfiOa3RhC5Pz6uXsYUJ4xexOUJaFKY3S8h9VaeaPxMyeA8oj9ssZC6tNLqNxqGzKJbHfSzQXofKwBH87e+du34mzqzm2apOMT2JVzxWmTwrl3JWnd2HG0odeVKMNsXLuQFN6jzCeJdLxHpu+dJOL6gJTW5t9AwoJ8jxmwO8xgUbk+7s38VATSuaV/RiIfXfGFv34CT7AY1gRxm1og9jjP6qkFMyZiO6M+lwrJIlHKTOKxw+xc15w/tIssUkeflzAcrkkNGzT8sBL39BoQOo9RTrMD2QL weather-balloon@wesley.iplantcollaborative.org",
        "ssh-rsa AAAAB3NzaC1yc2EAAAABIwAAAQEAo/O1gw1hn7I8sDgKGsIY/704O4/89JFO2AG2Quy9LCS5dO5HL40igFOUBmVkqy9ANPEMslaA5VwzPuP+ojKmDhTzoWc4wmvnCGjnZqaTW/+M+QfPSOKoyAaevKC4/Y2dxevS7eRdbeY5Pvweu5rf/eoCXF4DnGMWJ4C6IPVHy7gYpfZrdeiaYzxus53DvFNr4Dee9Y2jvY8wuS3EvL37DU1AGsv1UAN2IoOKZ9Itxwmhf/ZfnFyqMdebggceWRmpK/U2FuXewKMjoJ+HMWgzESR2Rit+9jGniiIVV3K5JeNmHqfWxu2BLpXDYEalX6l28opaiEbDevirwWmvoaAbDw== dboss",
        "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQCyORkWztT4EXpwP5T3voIL/hK683RlOrGh794CSklUiFxbM/Iag6TYqDV3diNmVLfNWXvDD/WATYrsn6bijDpMn7qPBwKeuTI1f2j3tBMluUw3dsavlC2VIyyIEbL0PnLrgiXa4/OpYxZmuD9GIf9eDlb6xYsFQ3B8ZimCCX6vqUVj8gyVNEt7JMWgrx8q1D0u0jWvN2wAMoSD9epMN0IpWEMB9cwNEHbU1Jt5upm1pTC3np7o008aZxJios05iVLdCkj5bTl/ZVxJ5ShIpECBW+h5I2y9MTzeCFOAAmqsbFJN3rjI2Q6u3DjPmvh3y4aF1wGOaYnQMbpnLTqACRsS0D6IofIfuxzSCABgCLc+R4g2IqimcnhGrp62qzyGW/bLkzxEZBhKwudl4fl+ghTqDAPcCQwssvbE466CuWaBuEvfdEQ+yHTe3Fgezri4C4nhF53ZzWynUM/9ajtkzSV53fU6W4RAdYdipsXKzXDa25y5maff2AnhrvewDuVY4mt4pba13ihw2rf3p/RWmHBdN4nulZkCWdm6eQ1VgDc+shU+LE9GOTOQNzibVO1n3mAdjxJyX3RYj/egSUlYqNbBeEAAbwmbFmJTuTWQgm63IMnliPrgJjLQtuU9ZV+SJUxyoV/6qPPZA0L2DYes4iWeMW43uVFOck8Yjik/d/Ar0Q== mattd@IPC-MARA.local",
        "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDiAFmfG+7QP4WK6EwiKo+v34bG9DywF6f0eXym5FJkc6NQPDeG13F/kZSayFqB4IhD40nEofuawaMsPHsjJpjUAXwwgfuPUgnLjiPiFzrxdynnaevsCEzen8TXgOfvhUMgZTz9WiU7SGzSz5Sum8FncjKVjk0uVxbX6K/0FlVCm554uCEkY1l7yP59GpFDVGrDtDDUxmf+MM9862zoMWo5v8ekiFOlnILQONS0DojAoCWCb9TGmI833kKqJtVNh1ZbDdTjL/iR2o1bEbBXN+2CoPA1ZDaE25O+BOGAKY0wAL+Yc8pzeKWV7N34KK4L91XfcGPPQWggZ7O0BgHg57Ez root@lofn ansible"]
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
        "127.0.0.1",
        "128.196.38.[1-127]",
        "128.196.64.[1-512]",
        "128.196.142.*",
        "128.196.172.[128-255]",
        "150.135.78.*",
        "150.135.93.[128-255]",
        "10.130.5.[128-155]",
        "10.140.65.*",
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
    # TODO: if not ldap package
    # TODO:     install ldap package
    ldap_replace()


def insert_modprobe():
    run_command(['depmod', '-a'])
    run_command(['modprobe', 'acpiphp'])


# File Operations
def line_in_file(needle, filename):
    found = False
    f = open(filename, 'r')
    for line in f:
        if needle in line:
            found = True
            break
    f.close()
    return found


def text_in_file(filename, text):
    file_contents = read_file(filename)
    if text in file_contents:
        return True
    return False


def read_file(filename):
    try:
        f = open(filename, 'r')
        content = f.read()
        f.close()
        return content
    except Exception as e:
        logging.exception("Error reading file %s" % filename)
        return ""


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


def redeploy_atmo_init(user, public_ip_hint):
    mount_storage()
    start_vncserver(user)
    start_shellinaboxd()
    distro = get_distro()
    start_ntp(distro)
    # Get IP addr//Hostname from instance metadata
    instance_metadata = get_metadata()
    hostname = get_hostname(instance_metadata, public_ip_hint)
    logging.debug("Distro - %s" % distro)
    logging.debug("Hostname - %s" % hostname)
    set_hostname(hostname, distro)


def deploy_atmo_init(user, instance_data, instance_metadata, root_password,
                     vnclicense, public_ip_hint):
    distro = get_distro()
    logging.debug("Distro - %s" % distro)
    linuxuser = user
    linuxpass = ""
    public_ip = get_public_ip(instance_metadata)
    hostname = get_hostname(instance_metadata, public_ip_hint)
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

    mount_storage()
    ldap_install()
    etc_skel_bashrc(linuxuser)
    run_command(['/bin/cp', '-rp',
                 '/etc/skel/.',
                 '/home/%s' % linuxuser])
    check_ldap(linuxuser)
    run_command(['/bin/chown', '-R',
                 '%s:iplant-everyone' % (linuxuser,),
                 '/home/%s' % linuxuser])
    run_command(['/bin/chmod', 'a+rwxt', '/tmp'])
    run_command(['/bin/chmod', 'a+rx', '/bin/fusermount'])
    run_command(['/bin/chmod', 'u+s', '/bin/fusermount'])
    vnc(linuxuser, distro, vnclicense)
    iplant_files(distro)
    idrop(linuxuser, distro)
    nagios()
    distro_files(distro)
    update_timezone()
    start_ntp(distro)
    shellinaboxd(distro)
    insert_modprobe()
    denyhost_whitelist()
    modify_rclocal(linuxuser, distro, hostname)


def is_executable(full_path):
    return os.path.isfile(full_path) and os.access(full_path, os.X_OK)


def run_boot_scripts():
    post_script_dir = "/etc/atmo/post-scripts.d"
    if not os.path.isdir(post_script_dir):
        # Nothing to execute.
        return
    post_script_log_dir = "/var/log/atmo/post-scripts"
    if not os.path.exists(post_script_log_dir):
        mkdir_p(post_script_log_dir)
    stdout_logfile = os.path.join(post_script_log_dir, "stdout")
    stderr_logfile = os.path.join(post_script_log_dir, "stderr")
    for file_name in os.listdir(post_script_dir):
        full_path = os.path.join(post_script_dir, file_name)
        try:
            if is_executable(full_path):
                logging.info("Executing post-boot script: %s" % full_path)
                output, error = run_command([full_path])
                output_file = open(stdout_logfile, 'a')
                if output_file:
                    output_file.write(
                        "--\n%s OUTPUT:\n%s\n" %
                        (full_path, output))
                    output_file.close()
                output_file = open(stderr_logfile, 'a')
                if output_file:
                    output_file.write(
                        "--\n%s ERROR:\n%s\n" %
                        (full_path, error))
                    output_file.close()
        except Exception as exc:
            logging.exception("Exception executing/logging the file: %s"
                              % full_path)


def add_zsh():
    if os.path.exists("/bin/zsh") and not os.path.exists("/usr/bin/zsh"):
        run_command(['ln', '-s', '/bin/zsh', '/usr/bin/zsh'])


def check_ldap(user):
    delay_time = 60  # in seconds
    max_tries = 60
    current_try = 0
    found = None
    while current_try < max_tries:

        current_try += 1
        try:
            found = pwd.getpwnam(user)
            break
        except KeyError as e:
            logging.debug(
                'check_ldap: failed, attempt #%d, waiting %d seconds' %
                (current_try, delay_time))
            time.sleep(delay_time)

    if not found:
        raise Exception(
            "Failed to contact ldap within %d seconds" %
            (delay_time * max_tries))


def start_ntp(distro):
    if is_rhel(distro):
        if os.path.exists("/etc/init.d/ntpd"):
            run_command(["/etc/init.d/ntpd", "restart"])
    elif os.path.exists("/etc/init.d/ntp"):
        run_command(["/etc/init.d/ntp", "restart"])


def main(argv):
    init_logs('/var/log/atmo/atmo_init_full.log')
    instance_data = {"atmosphere": {}}
    public_ip_hint = None
    service_type = None
    instance_service_url = None
    instance_service_url = None
    server = None
    root_password = None
    user_id = None
    redeploy = False
    vnclicense = None
    try:
        opts, args = getopt.getopt(
            argv, "rt:u:s:i:T:N:v:",
            ["redeploy", "service_type=", "service_url=", "server=",
             "user_id=", "token=", "name=", "vnc_license=", "root_password="])
    except getopt.GetoptError:
        logging.error("Invalid arguments provided.")
        sys.exit(2)
    for opt, arg in opts:
        if opt in ("--public-ip"):
            instance_data["atmosphere"]["public_ip_hint"] = arg
            public_ip_hint = arg
        elif opt in ("-t", "--service_type"):
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
        elif opt in ("-r", "--redeploy"):
            redeploy = True
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
    global ATMO_INIT_FILES
    ATMO_INIT_FILES = "%s/api/v1/init_files" % ATMOSERVER
    logging.debug("Atmosphere init files location- %s" % ATMO_INIT_FILES)
    set_user_home_dir()
    add_zsh()
    if redeploy:
        redeploy_atmo_init(user_id, public_ip_hint)
    else:
        instance_metadata = get_metadata()
        logging.debug("Instance metadata - %s" % instance_metadata)
        deploy_atmo_init(user_id, instance_data, instance_metadata,
                         root_password, vnclicense, public_ip_hint)
    logging.info("Atmo Init Completed.. Checking for boot scripts.")
    run_boot_scripts()


if __name__ == "__main__":
    main(sys.argv[1:])
