"""
imaging/clean.py

These functions are used to strip data from a VM before imaging occurs.

"""
from service.imaging.common import remove_files, overwrite_files,\
                                   remove_line_in_files,\
                                   replace_line_in_files,\
                                   remove_multiline_in_files,\
                                   run_command,\
                                   check_mounted,\
                                   prepare_chroot_env,\
                                   remove_chroot_env


def remove_user_data(mounted_path, dry_run=False):
    """
    Remove user data from an image that has already been mounted
    """
    if not check_mounted(mounted_path):
        raise Exception("Expected a mounted path at %s" % mounted_path)
    remove_files = ['home/*', ]
    overwrite_files = ['', ]
    remove_line_files = []
    replace_line_files = [
        #('replace_pattern','replace_with','in_file'),
        ("users:x:100:.*", "users:x:100:", "etc/group"),
        #TODO: Check this should not be 'AllowGroups users core-services root'
        ("AllowGroups users root.*", "", "etc/ssh/sshd_config"),
    ]
    multiline_delete_files = [
        #('delete_from', 'delete_to', 'replace_where')
    ]
    _perform_cleaning(mounted_path, rm_files=remove_files,
                      remove_line_files=remove_line_files,
                      overwrite_list=overwrite_files,
                      replace_line_files=replace_line_files, 
                      multiline_delete_files=multiline_delete_files,
                      dry_run=dry_run)


def remove_atmo_data(mounted_path, dry_run=False):
    """
    Remove atmosphere data from an image that has already been mounted
    """
    if not check_mounted(mounted_path):
        raise Exception("Expected a mounted path at %s" % mounted_path)
    remove_files = [#Atmo
                    'etc/rc.local.atmo',
                    'usr/sbin/atmo_boot.py',
                    'var/log/atmo/atmo_boot.log',
                    'var/log/atmo/atmo_init.log',
                    'var/log/atmo/atmo_init_full.log',
                    'var/log/atmo/shellinaboxd.log',
                    'var/log/atmo/deploy.log',
                    #Puppet
                    'var/lib/puppet/run/*.pid',
                    'etc/puppet/ssl', 
                    'var/log/puppet',
                   ]
    overwrite_files = []
    remove_line_files = []
    replace_line_files = [
        #('replace_pattern','replace_with','in_file'),
        (".*vncserver$", "", "etc/rc.local"),
        (".*shellinbaox.*", "", "etc/rc.local")
    ]
    multiline_delete_files = [
        #TEMPLATE:
        #('delete_from', 'delete_to', 'replace_where')

        ("## Atmosphere System", "# End Nagios", "etc/sudoers"),
        #Just in case nagios isn't there..
        ("## Atmosphere System", "# End Atmosphere System", "etc/sudoers"),
        ("## Atmosphere System", "## End Atmosphere System",
         "etc/ssh/sshd_config"),

        #Remove lines below after next maintenance period..
        ("## Atmosphere System", "Allowgroups users root core-services",
         "etc/ssh/sshd_config"),
        #Remove lines above after next maintenance period..

        ("## Atmosphere System", "## End Atmosphere System",
         "etc/skel/.bashrc"),
    ]
    _perform_cleaning(mounted_path, rm_files=remove_files,
                      remove_line_files=remove_line_files,
                      overwrite_list=overwrite_files,
                      replace_line_files=replace_line_files, 
                      multiline_delete_files=multiline_delete_files,
                      dry_run=dry_run)
    

def remove_vm_specific_data(mounted_path, dry_run=False):
    """
    Remove "VM specific data" from an image that has already been mounted
    this data should include:
    * Logs
    * Pids
    * dev, proc, ...
    """
    if not check_mounted(mounted_path):
        raise Exception("Expected a mounted path at %s" % mounted_path)
    remove_files = ['mnt/*', 'tmp/*', 'root/*', 'dev/*',
                    'proc/*',
                   ]
    remove_line_files = []
    overwrite_files = [
        'root/.bash_history', 'var/log/auth.log',
        'var/log/boot.log', 'var/log/daemon.log',
        'var/log/denyhosts.log', 'var/log/dmesg',
        'var/log/secure', 'var/log/messages',
        'var/log/lastlog', 'var/log/cups/access_log',
        'var/log/cups/error_log', 'var/log/syslog',
        'var/log/user.log', 'var/log/wtmp',
        'var/log/apache2/access.log',
        'var/log/apache2/error.log',
        'var/log/yum.log']
    replace_line_files = [
        #('replace_pattern','replace_with','in_file'),
    ]
    multiline_delete_files = [
        #('delete_from', 'delete_to', 'replace_where')
    ]
    _perform_cleaning(mounted_path, rm_files=remove_files,
                      remove_line_files=remove_line_files,
                      overwrite_list=overwrite_files,
                      replace_line_files=replace_line_files, 
                      multiline_delete_files=multiline_delete_files,
                      dry_run=dry_run)


def _perform_cleaning(mounted_path, rm_files=None,
                      remove_line_files=None, overwrite_list=None,
                      replace_line_files=None, multiline_delete_files=None,
                      dry_run=False):
    """
    Runs the commands to perform all cleaning operations.
    For more information see the specific function
    """
    remove_files(rm_files, mounted_path, dry_run)
    overwrite_files(overwrite_list, mounted_path, dry_run)
    remove_line_in_files(remove_line_files, mounted_path, dry_run)
    replace_line_in_files(replace_line_files, mounted_path, dry_run)
    remove_multiline_in_files(multiline_delete_files, mounted_path, dry_run)


def remove_ldap(mounted_path, new_password='atmosphere'):
    try:
        prepare_chroot_env(mounted_path)
        run_command(["/usr/sbin/chroot", mounted_path, "/bin/bash", "-c",
                     "echo %s | passwd root --stdin" % new_password])
        run_command(["/usr/sbin/chroot", mounted_path, 'yum',
                     'remove', '-qy', 'openldap'])
    finally:
        remove_chroot_env(mounted_path)

def remove_vnc(mounted_path):
    try:
        prepare_chroot_env(mounted_path)
        run_command(["/usr/sbin/chroot", mounted_path, 'yum',
            'remove', '-qy', 'realvnc-vnc-server'])
        #remove rpmsave.. to get rid of vnc for good.
        #["/usr/sbin/chroot", mounted_path, 'find', '/',
        #'-type', 'f', '-name', '*.rpmsave', '-exec', 'rm', '-f',
        #'{}', ';']
    finally:
        remove_chroot_env(mounted_path)

