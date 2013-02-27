#!/usr/bin/env python
import getopt
import logging
import os, errno
import re
import time
import urllib2
import subprocess
import sys

try:
    from hashlib import sha1
except ImportError:
    #Support for python 2.4
    from sha import sha as sha1

ATMOSERVER=""
SCRIPT_VERSION=30

def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc: # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else: raise

def touch(fname, times=None):
    with file(fname, 'a'):
        os.utime(fname, times)

def init_logs(log_file):
    mkdir_p('/var/log/atmo/') # NOTE: Can't use run_command yet.
    touch('/var/log/atmo/atmo_init_full.log')
    format = "%(asctime)s %(name)s-%(levelname)s [%(pathname)s %(lineno)d] %(message)s"
    logging.basicConfig(
            level=logging.DEBUG,
            format = format,
            filename = log_file,
            filemode = 'a+')

def download_file(url,fileLoc,retry=False, match_hash=None):
    waitTime = 0
    attempts = 0
    contents = None
    logging.debug('Downloading file: %s' % url)
    while True:
        attempts += 1
        logging.debug('Attempt: %s, Wait %s seconds' % (attempts,waitTime))
        time.sleep(waitTime)
        #Exponential backoff * 10s = 20s,40s,80s,160s,320s...
        waitTime = 10 * 2**attempts
        try:
            resp = urllib2.urlopen(url)
        except Exception, e:
            logging.error(e)
            resp = None

        #Download file on success
        if resp is not None and resp.code == 200:
            contents = resp.read()
        #EXIT condition #1: Non-empty file found
        if contents is not None and len(contents) != 0:
            logging.debug('Downloaded file')
            break
        #EXIT condition #2: Don't want to try again
        if not retry:
            break
        #Retry condition: Retry is true && file is empty
    #Save file if hash matches
    try:
        file_hash = sha1(contents).hexdigest()
    except Exception, e:
        file_hash = ""
        logging.error(e)
    #Don't save file if hash exists and doesnt match..
    if match_hash and match_hash != file_hash:
        logging.warn("Error, The downloaded file <%s - SHA1:%s> does not match expected SHA1:%s" % ( url, file_hash, match_hash))
        return ""
    logging.debug('Saving url:%s to file: %s' % (url,fileLoc))
    f = open(fileLoc,"w")
    f.write(contents)
    f.close()
    return contents

def get_distro():
    if os.path.isfile('/etc/redhat-release'):
        return 'rhel'
    else:
        return 'ubuntu'

def run_command(commandList, shell=False):
    out = None
    err = None
    logging.debug("RunCommand:%s" % ' '.join(commandList))
    try:
        proc = subprocess.Popen(commandList, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=shell)
        out,err = proc.communicate()
    except Exception, e:
        logging.error(e)
    logging.debug(out)
    logging.debug(err)
    return (out,err)

def add_etc_group(user):
    run_command(["/bin/sed -i 's/users:x:.*/&#%s,/' /etc/group" % (user,)])

def comment_test(filename):
    if '## Atmosphere System' in open(filename).read():
        return True
    return False

def add_sudoers(user):
    f = open("/etc/sudoers","a")
    f.write("""## Atmosphere System
%s ALL=(ALL)ALL
""" % user)
    f.close()

def restart_ssh(distro):
    if 'rhel' in distro:
        run_command(["/etc/init.d/sshd","restart"])
    else:
        run_command(["/etc/init.d/ssh","restart"])

def ssh_config():
    f = open("/etc/ssh/sshd_config","a")
    f.write("""## Atmosphere System
AllowGroups users core-services root
""")
    f.close()
    restart_ssh(distro)

def collect_metadata():
    METADATA_SERVER='http://128.196.172.136:8773/latest/meta-data/'
    metadata = {}
    meta_list = []
    try:
        resp = urllib2.urlopen(METADATA_SERVER)
        content = resp.read()
        meta_list = content.split('\n')
    except Exception, e:
        logging.error("Could not retrieve meta-data for instance")
        logging.error(e)
        return {}

    for meta in meta_list:
        print meta
        try:
            resp = urllib2.urlopen('http://128.196.172.136:8773/latest/meta-data/'+meta)
            content = resp.read()
            if meta.endswith('/'):
                content_list = content.split('\n')
                for content in content_list:
                    print "new meta: %s%s"% (meta,content)
                    meta_list.append("%s%s" % (meta,content))
            else:
                metadata[meta] = content
        except Exception, e:
            metadata[meta] = None
    return metadata

def mount_home():
    """
    Is this a hack? Mount the second device if it's partition size is larger
    User should have the most available space, and that will be second partition
    if the size of instance is > medium/large/etc.
    """
    logging.debug("Mount test")
    (out,err) = run_command(['/sbin/fdisk','-l'])
    if 'sda1' in out:
        dev_1 = 'sda1'
        dev_2 = 'sda2'
    else:
        dev_1 = 'xvda1'
        dev_2 = 'xvda2'
    outLines = out.split('\n')
    for line in outLines:
        r = re.compile(', (.*?) bytes')
        match = r.search(line)
        if dev_1 in line:
            dev_1_size = match.group(1)
        elif dev_2 in line:
            dev_2_size = match.group(1)
    if dev_2_size > dev_1_size:
        logging.warn("%s is larger than %s, Mounting %s to home" % (dev_2, dev_1, dev_2))
        run_command(["/bin/mount","-text3", "/dev/%s" % dev_2, "/home"])

def vnc(user, distro):
    try:
        if not os.path.isfile('/usr/bin/vnclicense'):
            logging.debug("VNC not installed, license not found on machine")
            return
        #ASSERT: VNC server installed on this machine
        if distro == 'rhel5':
            run_command(['/usr/bin/yum','-qy','remove','vnc-E','realvnc-vnc-server'])
            download_file('%s/init_files/%s/VNC-Server-5.0.4-Linux-x64.rpm' % (ATMOSERVER,SCRIPT_VERSION), "/opt/VNC-Server-5.0.4-Linux-x64.rpm", match_hash='0c59f2d84880a6848398870e5f0aa39f09e413bc')
            run_command(['/bin/rpm','-Uvh','/opt/VNC-Server-5.0.4-Linux-x64.rpm'])
            run_command(['/bin/sed', '-i', "'$a account    include      system-auth'", '/etc/pam.d/vncserver.custom'])
            run_command(['/bin/sed', '-i', "'$a password   include      system-auth'", '/etc/pam.d/vncserver.custom'])
        else:
            download_file('%s/init_files/%s/VNC-Server-5.0.4-Linux-x64.deb' % (ATMOSERVER,SCRIPT_VERSION), "/opt/VNC-Server-5.0.4-Linux-x64.deb", match_hash='c2b390157c82fd556e60fe392b6c5bc5c5efcb29')
            run_command(['/usr/bin/dpkg','-i','/opt/VNC-Server-5.0.4-Linux-x64.deb'])
            with open('/etc/pam.d/vncserver.custom', 'w') as new_file:
                new_file.write("auth include  common-auth")
            with open('/etc/vnc/config.d/common.custom', 'w') as new_file:
                new_file.write("PamApplicationName=vncserver.custom")
        time.sleep(1)
        run_command(['/usr/bin/vnclicense','-add','7S532-626QV-HNJP4-2H7CQ-W5Z8A'])
        download_file('%s/init_files/%s/vnc-config.sh' % (ATMOSERVER,SCRIPT_VERSION), os.environ['HOME'] + '/vnc-config.sh', match_hash='37b64977dbf3650f307ca0d863fee18938038dce')
        run_command(['/bin/chmod','a+x', os.environ['HOME'] + '/vnc-config.sh'])
        run_command([os.environ['HOME'] + '/vnc-config.sh'])
        run_command(['/bin/su','%s' % user, '-c', '/usr/bin/vncserver'])
    except Exception, e:
        logging.error(e)

def iplant_files():
    download_file('http://www.iplantcollaborative.org/sites/default/files/atmosphere/fuse.conf', '/etc/fuse.conf', match_hash='21d4f3e735709827142d77dee60befcffd2bf5b1')

    download_file("http://www.iplantcollaborative.org/sites/default/files/atmosphere/atmoinfo", "/usr/local/bin/atmoinfo", match_hash="0f6426df41a5fe139515079060ab1758e844e20c")
    run_command(["/bin/chmod","a+x","/usr/local/bin/atmoinfo"])

    download_file("http://www.iplantcollaborative.org/sites/default/files/atmosphere/xprintidle", "/usr/local/bin/xprintidle", match_hash="5c8b63bdeab349cff6f2bf74277e9143c1a2254f")
    run_command(["/bin/chmod","a+x","/usr/local/bin/xprintidle"])

    download_file("http://www.iplantcollaborative.org/sites/default/files/atmosphere/atmo_check_idle.py", "/usr/local/bin/atmo_check_idle.py", match_hash="ab37a256e15ef5f529b4f4811f78174265eb7aa0")
    run_command(["/bin/chmod","a+x","/usr/local/bin/atmo_check_idle.py"])

    run_command(["/bin/mkdir","-p","/opt/irodsidrop"])
    download_file("http://www.iplantcollaborative.org/sites/default/files/irods/idrop20120628.jar", "/opt/irodsidrop/idrop-latest.jar", match_hash="536e56760c8c993d0f6fd5c533d43a61fa0be805")
    #download_file("http://www.iplantcollaborative.org/sites/default/files/idroprun.sh.txt", "/opt/irodsidrop/idroprun.sh", match_hash="0e9cec8ce1d38476dda1646631a54f6b2ddceff5")
    #run_command(['/bin/chmod','a+x','/opt/irodsidrop/idroprun.sh'])


def shellinaboxd():
    download_file('%s/init_files/%s/shellinaboxd-install.sh' % (ATMOSERVER,SCRIPT_VERSION), os.environ['HOME'] + '/shellinaboxd-install.sh', match_hash='a2930f7cfe32df3d3d2e991e01cb0013d1071f15')
    run_command(['/bin/chmod','a+x', os.environ['HOME'] + '/shellinaboxd-install.sh'])
    run_command([os.environ['HOME'] + '/shellinaboxd-install.sh'], shell=True)
    run_command(['rm -rf ' + os.environ['HOME'] + '/shellinabox*'], shell=True)

def atmo_cl():
    download_file('%s/init_files/%s/atmocl' % (ATMOSERVER,SCRIPT_VERSION), '/usr/local/bin/atmocl', match_hash='28cd2fd6e7fd78f1b58a6135afa283bd7ca6027a')
    download_file('%s/init_files/%s/AtmoCL.jar' % (ATMOSERVER,SCRIPT_VERSION), '/usr/local/bin/AtmoCL.jar', match_hash='24c6acb7184c54ba666134120ac9073415a5b947')
    run_command(['/bin/chmod','a+x','/usr/local/bin/atmocl'])

def nagios():
    download_file('%s/init_files/%s/nrpe-snmp-install.sh' % (ATMOSERVER,SCRIPT_VERSION), os.environ['HOME'] + '/nrpe-snmp-install.sh', match_hash='12da9f6f57c79320ebebf99b5a8516cc83c894f9')
    #download_file('%s/init_files/%s/nrpe-snmp-install.sh' % (ATMOSERVER,SCRIPT_VERSION), '/root/nrpe-snmp-install.sh', match_hash='d8b8c5a7c713b65c5ebdff409b3439cda6c73c00')
    run_command(['/bin/chmod','a+x', os.environ['HOME'] + '/nrpe-snmp-install.sh'])
    run_command([os.environ['HOME'] + '/nrpe-snmp-install.sh'])

def deploy_atmo_boot():
    download_file('%s/init_files/%s/atmo_boot.py' % (ATMOSERVER,SCRIPT_VERSION), '/usr/sbin/atmo_boot', match_hash='e6bef1f831f81939a325084123a3d064c4845b5f')
    run_command(['/bin/chmod','a+x','/usr/sbin/atmo_boot'])
    run_command(['/bin/sed','-i',"'s/\/usr\/bin\/ruby \/usr\/sbin\/atmo_boot/\/usr\/sbin\/atmo_boot/'", '/etc/rc.local'])

def notify_launched_instance(atmoObj, metadata):
    try:
        import json
    except ImportError:
        #Support for python 2.4
        import simplejson as json
    from httplib2 import Http
    service_url = atmoObj['atmosphere']['instance_service_url']
    userid = atmoObj['atmosphere']['userid']
    instance_token = atmoObj['atmosphere']['instance_token']
    data = {
            'action':'instance_launched',
            'userid':userid,
            'vminfo':metadata,
            'arg':atmoObj,
            'token':instance_token,
           }
    h = Http(disable_ssl_certificate_validation=True)
    headers = {'Content-type': 'application/json'}
    resp, content = h.request(service_url, "POST", headers=headers, body=json.dumps(data))
    logging.debug(resp)
    logging.debug(content)

def distro_files(distro, metadata):
    if 'rhel' in distro:
        #Rhel path
        download_file('http://www.iplantcollaborative.org/sites/default/files/atmosphere/motd','/etc/motd', match_hash='b8ef30b1b7d25fcaf300ecbc4ee7061e986678c4')
        download_file('http://www.iplantcollaborative.org/sites/default/files/irods/irodsFs_v31.rhel5.x86_64', '/usr/local/bin/irodsFs.x86_64', match_hash='ea3b26f3d589c5ea8a72349b640e76f60a0b570c')
        run_command(['/etc/init.d/iptables','stop'])
        run_command(['/usr/bin/yum','-y','-q','install','emacs'])
    else:
        #Ubuntu path
        download_file('http://www.iplantcollaborative.org/sites/default/files/atmosphere/motd','/etc/motd.tail', match_hash='b8ef30b1b7d25fcaf300ecbc4ee7061e986678c4')
        download_file('http://www.iplantcollaborative.org/sites/default/files/irods/irodsFs_v31.ubuntu10.x86_86', '/usr/local/bin/irodsFs.x86_64', match_hash='22cdaae144bad55f9840a704ef9f0385f7dc8274')
        run_command(['/usr/bin/apt-get','-y','-q','install','vim'])
        #hostname = metadata['public-ipv4'] #kludge
        #run_command(['/bin/hostname', '%s' % hostname]) #kludge
    run_command(['/bin/chmod','a+x','/usr/local/bin/irodsFs.x86_64'])

def install_icommands(distro):
    pass
def update_timezone():
    run_command(['/bin/rm','/etc/localtime'])
    run_command(['/bin/ln','-s','/usr/share/zoneinfo/US/Arizona','/etc/localtime'])

def run_update_sshkeys(sshdir, sshkeys):
    authorized_keys = sshdir + '/authorized_keys'
    f = open(authorized_keys,'a')
    for key in sshkeys:
        f.write(key+'\n')
    f.close()

def update_sshkeys():
    sshkeys = [
        "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQDGjaoIl/h8IcgqK7U9i0EVYMPFad6NdgSV8gsrNLQF93+hkWEciqpX9TLn6TAcHOaL0xz7ilBetG3yaLSZBHaoKNmVCBaziHoCJ9wEwraR6Vw87iv3Lhfg/emaQiJIZF3YnPKcDDB1/He9Cnz//Y+cjQbYxLeJWdVi/irZKEWhkotb3xyfrf4o05FvLEzvaMbmf3XS1J0Rtu7BqPOvNl+U0ZqS57tNoqG2C6Cf10E340iqQGTgXzOrDmd+Rof2G1IkyKlW60okAa2N+Z8BCRB27hHY5bcS1vvnO6lo8VzWxbU3Z2MCbk1So9wHV8pAXyF1+MnVc6aJUs1xc/Lni1Xbp5USs6kOvyew3HaN3UDnoC1FSMDguAriwxho882NM/LRpGJFui2i/H3GYgQ1KQwBRqLTWEY9H8Qvy5RuOG36cy4jWJMxh6YoxOyDpZP6UlONiyuwwqrVCjUeHwIDHdBq1RGBJIEBsYhGFCYEP3UotGwEvGo7vGfb3eAebbPMsj8TAP3eR/XCd7aIeK6ES9zfNJfD2mjJqGHMUeFgbiDmTPfjGOxZ53bZssEjb0BbXNvFPezj8JetfbHZE4VUjDAUcOrLp6NT9yG6hbWFdGQxyqIbKSeMabDu8gxAcqFJvi2yFMV5j0F3qQiAPUwrigr98c4+aLvKqwsRvHxWUETBOw== idle time daemon",
        "ssh-rsa AAAAB3NzaC1yc2EAAAABIwAAAQEAvTEkREh5kmUAgx61pB0ikyH0swoXRId6yhGwIdm8KQgjErWSF8X4MED8t+7Pau98/mzxuvA23aiIn7MQWSQWQVQBFGZqj4losf+oEBS+ZQGJf2ocx3DP3NStgnixKgiDId6wjPTF1s9/YLntNb4ZNGvBSDg0bxzDJWoQ9ghOpHXmqFDWHxE9jr1qLHZzqQ0Pt1ATCW+OJ/b2staqVDPSa1SwMI89Cuw7iiSWfNHML1cf0wbYU3Bg+jT5GlwCojWP/yHqDCF1t3XL0xZQlWdKt7fM6bKUonv1CGcRZO22npZwX5Uv3U5OlskSFJnr8oZZV6V6kn99gwNzZnmiK32QQQ== edwins@iplant",
        "ssh-rsa AAAAB3NzaC1yc2EAAAABIwAAAQEAxB+KLO6pTeZ9ye/GuT2i74LBl4lvfJm7ESo4O9tNJtIf8fcAHqm9HMr2dQBixxdsLUYjVyZLZM8mZQdEtLLvdd4Fqlse74ci4RIPTgvlgwTz6dRJfABD9plTM5r5C2Rc6jLur8iVR40wbHmbgLgcilXoYnRny4bFoAhfAHt2vxiMY6wnhiL9ESSUA/i1LrcYcGj2QAvAPLf2yTJFtXSCwnlBIJBjMASQiPaIU2+xUyQisgSF99tBS3DZyu4NVGnSGYGmKl84CEFp+x57US4YAl9zuAnM9ckTp4mOjStEvIpyyPJA03tDbfObSi50Qh5zta9I1PIAGxOznT6dJbI1bw== aedmonds@iplant",
        "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDgvgRtXgkvM/+eCSEqVuTiUpZMjRfA9AnXfz0YWS93uKImoodE5oJ7wUZqjpOmgXyX0xUDI4O4bCGiWVmSyiRiQpqZrRrF7Lzs4j0Nf6WvbKblPQMwcmhMJuaI9CwU5aEbEqkV5DhBHcUe4bFEb28rOXuUW6WMLzr4GrdGUMd3Fex64Bmn3FU7s6Av0orsgzVHKmoaCbqK2t3ioGAt1ISmeJwH6GasxmrSOsLLW+L5F65WrYFe0AhvxMsRLKQsuAbGDtFclOzrOmBudKEBLkvwkblW8PKg06hOv9axNX7C9xlalzEFnlqNWSJDu1DzIa2NuOr8paW5jgKeM78yuywt jmatt@leia",
        "ssh-rsa AAAAB3NzaC1yc2EAAAABIwAAAQEA2TtX9DohsBaOEoLlm8MN+W+gVp40jyv752NbMP/PV/LAz5MnScJcvbResAJx2AusL1F6sRNvo9poNZiab6wpfErQPZLfKGanPZGYSdonsNAhTu/XI+4ERPQXUA/maQ2qZtL1b+bmZxg9n/5MsZFpA1HrXP3M2LzYafF2IzZYWfsPuuZPsO3m/cUi0G8n7n0IKXZ4XghjGP5y/kmh5Udy9I5qreaTvvFlNJtBE9OL39EfWtjOxNGllwlGIAdsljfRxkeOzlahgtCJcaoW7X2A7GcV52itUwMKfTIboAXnZriwh5n0o1aLHCCdUAGDGHBYmP7fO7/2gIQKgpLfRkDEiQ== sangeeta@iplant",
        "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC+SYMny6H2B5IjXe6gxofHRNza5LE3NqTCe6YgYnnzYjyXWtopSeb8mK2q1ODzlaQyqYoTvPqtn6rSyN+5oHGV4o6yU+Fl664t5rOdAwz/jGJK3WwG60Pc0eGQco0ldgjD7K6LWYVPIJZs+rGpZ70jF5JsTuHeplXOn5MX9oUvNxxgXRuySxvBNOGMn0RxydK8tBTbZMlJ5MkAi/bIOrEDHEfejCxKGWITpXGkdTS2s4THiY8WqFdHUPtQkEfQkXCsRpZ6HPw1gN+JYD5NI38dVVmrA+3MgFVJkwtLUbbAM0yxgKwaUaipNN1+DeYOxBuVRlRwrrAp3+fq+4QCJrXd root@dalloway",
    "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDGCC+Q1yS/9iDkYyrVEFpE7qWFXK/2QSX6Fa1mNKWZiopztmzfEeqUYtiPRqyXSH6M6+L/sjR2TVfI8CzAB+pW42sPoTjER9tfPad8yV7JmCZPGAekI4/2COj3gDuGc9TcX2Dfu+h14M2hUhC8sJsomUm+0ALzBfSSFD4sF+4jDfZSbjrUzelDE11UFDNenGx9pNRVwXLNuxwqv8To9U3C7/ZdO8o3+jL1m4LT+8dGgAp+a0Eq99fTi86fmg1sRri2OJLngEDCEjutPckmXhF2Db3wo3R/I0I7nUXkXf0LfEFWNSaZdXYvIscWzm8P8yaK+GieGtNaB7fBscogLELT root@mickey",
        ]
    root_ssh_dir = '/root/.ssh'
    mkdir_p(root_ssh_dir)
    run_update_sshkeys(root_ssh_dir, sshkeys)
    if os.environ['HOME'] != '/root':
        home_ssh_dir = os.environ['HOME'] + '/.ssh'
        mkdir_p(home_ssh_dir)
        run_update_sshkeys(home_ssh_dir, sshkeys)

def update_sudoers():
    run_command(['/bin/sed','-i',"s/^Defaults    requiretty/#Defaults    requiretty/",'/etc/sudoers'])

def ldap_replace():
    run_command(['/bin/sed','-i',"s/128.196.124.23/ldap.iplantcollaborative.org/",'/etc/ldap.conf'])

def main(argv):
    init_logs('/var/log/atmo/atmo_init_full.log')
    atmoObj = {'atmosphere': {}}
    service_type = None
    instance_service_url = None
    servier = None
    user_id = None
    try:
        opts, args = getopt.getopt(argv, 
                                   "t:u:s:i:T:", 
                                   ["service_type=", "service_url=", "server=", "user_id=","token=" ])
    except getopt.GetoptError:
        logging.error("Invalid arguments provided.")
        sys.exit(2)
    for opt, arg in opts:
        if opt in ("-t", "--service_type"):
            atmoObj["atmosphere"]["service_type"] = arg
            service_type = arg
        elif opt in ("-T", "--token"):
            atmoObj["atmosphere"]["instance_token"] = arg
            instance_token = arg
        elif opt in ("-u", "--service_url"):
            atmoObj["atmosphere"]["instance_service_url"] = arg
            instance_service_url = arg
        elif opt in ("-s", "--server"):
            atmoObj["atmosphere"]["server"] = arg
            global ATMOSERVER
            ATMOSERVER = arg
            server = arg
        elif opt in ("-i", "--user_id"):
            atmoObj["atmosphere"]["userid"] = arg
            user_id= arg
        elif opt == '-d':
            global _debug
            _debug = 1
            logging.setLevel(logging.DEBUG)

    source = "".join(args)    

    linuxuser = atmoObj['atmosphere']['userid']
    linuxpass = ""
    logging.debug("Atmoserver - %s" % ATMOSERVER)
    distro = get_distro()
    logging.debug("Distro - %s" % distro)
    #TODO: Test this is multi-call safe
    #Add linux user to etc-group
    #comment_test determines if this sensitive file needs
    update_sshkeys()
    update_sudoers()
    if comment_test('/etc/sudoers'):
        add_etc_group(linuxuser)
        add_sudoers(linuxuser)
        ssh_config()

    instance_metadata = collect_metadata()
    #TODO: REMOVE THIS LEGACY CRAP!
    instance_metadata['linuxusername'] = linuxuser
    instance_metadata["linuxuserpassword"] = linuxpass
    instance_metadata["linuxuservncpassword"] = linuxpass
    #mount_home() #kludge
    run_command(['/bin/cp','-rp','/etc/skel/.','/home/%s' % linuxuser])
    run_command(['/bin/chown','-R', '%s:iplant-everyone' % (linuxuser,), '/home/%s' % linuxuser])
    run_command(['/bin/chmod','a+rx','/bin/fusermount'])
    run_command(['/bin/chmod','u+s','/bin/fusermount'])
    vnc(linuxuser, distro)
    run_command(['/bin/chmod','a+rwxt','/tmp'])
    iplant_files()
    atmo_cl()
    nagios()
    ldap_replace()
    #deploy_atmo_boot()
    distro_files(distro, instance_metadata)
    install_icommands(distro)
    update_timezone()
    shellinaboxd()
    logging.info("Complete.")

if __name__ == "__main__":
    main(sys.argv[1:])
