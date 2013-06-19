"""
imaging/clean.py

These functions are used to strip data from a VM before imaging occurs.

"""
from service.system_calls import wildcard_remove, 
def remove_user_data(mounted_path):
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
        ("\(users:x:100:\).*", "users:x:100:", "etc/group"),
        #TODO: Check this should not be 'AllowGroups users core-services root'
        ("AllowGroups users root.*", "", "etc/ssh/sshd_config"),
    ]
    multiline_delete_files = [
        #('delete_from', 'delete_to', 'replace_where')
    ]
    _perform_cleaning(mounted_path, remove_files=remove_files,
                      remove_line_files=remove_line_files,
                      overwrite_files=overwrite_files,
                      replace_line_files=replace_line_files, 
                      multiline_delete_files=multiline_delete_files,
                      dry_run=dry_run)


def remove_atmo_data(mounted_path):
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
    overwrite_files = ['', ]
    remove_line_files = []
    replace_line_files = [
        #('replace_pattern','replace_with','in_file'),
        (".*vncserver$", "", "etc/rc.local"),
        (".*shellinbaox.*", "", "etc/rc.local")
    ]
    multiline_delete_files = [
        #('delete_from', 'delete_to', 'replace_where')
        ("## Atmosphere system", "# End Nagios", "etc/sudoers"),
        ("## Atmosphere", "AllowGroups users core-services root",
         "etc/ssh/sshd_config")]:
    ]
    _perform_cleaning(mounted_path, remove_files=remove_files,
                      remove_line_files=remove_line_files,
                      overwrite_files=overwrite_files,
                      replace_line_files=replace_line_files, 
                      multiline_delete_files=multiline_delete_files,
                      dry_run=dry_run)
    

def remove_vm_specific_data(mounted_path):
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
        'var/log/secure', 'var/log/messages'
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
    _perform_cleaning(mounted_path, remove_files=remove_files,
                      remove_line_files=remove_line_files,
                      overwrite_files=overwrite_files,
                      replace_line_files=replace_line_files, 
                      multiline_delete_files=multiline_delete_files,
                      dry_run=dry_run)


def _perform_cleaning(mounted_path, remove_files=None,
                      remove_line_files=None, overwrite_files=None,
                      replace_line_files=None, multiline_delete_files=None,
                      dry_run=False):
    """
    Runs the commands to perform all cleaning operations.
    For more information see the specific function
    """
    _remove_files(remove_files, dry_run)
    _overwrite_files(overwrite_files, dry_run)
    _remove_line_in_files(remove_line_files, dry_run)
    _replace_line_in_files(replace_line_files, dry_run)
    _remove_multiline_in_files(multiline_delete_files, dry_run)

def _append_line_in_files(append_files, dry_run=False):
    for (append_line, append_to) in append_files:
        append_to = _check_mount_path(append_to)
        mounted_filepath = os.path.join(mount_point, append_to)
        sed_append(append_line, mounted_filepath, dry_run=dry_run)

def _prepend_line_in_files(prepend_files, dry_run=False):
    for (prepend_line, prepend_to) in prepend_files:
        prepend_to = _check_mount_path(prepend_to)
        mounted_filepath = os.path.join(mount_point, prepend_to)
        sed_prepend(prepend_line, mounted_filepath, dry_run=dry_run)



def _remove_files(remove_files, dry_run=False):
    """
    #Removes file (Matches wildcards)
    """
    for rm_file in remove_files:
        rm_file = _check_mount_path(rm_file)
        rm_file_path = os.path.join(mount_point, rm_file)
        wildcard_remove(rm_file_path, dry_run=dry_run)


def _overwrite_files(overwrite_files, dry_run=False):
    """
    #Copy /dev/null to clear sensitive logging data
    """
    for overwrite_file in overwrite_files:
        overwrite_file = _check_mount_path(overwrite_file)
        overwrite_file_path = os.path.join(mount_point, overwrite_file)
        overwrite_file(overwrite_file_path, dry_run=dry_run)


def _remove_line_in_files(remove_line_files, dry_run=False):
    """
    #Single line removal..
    """
    for (remove_line_w_str, remove_from) in remove_line_files:
        remove_from = _check_mount_path(remove_from)
        mounted_filepath = os.path.join(mount_point, remove_from)
        sed_delete_one(remove_line_w_str, mounted_filepath, dry_run=dry_run)


def _replace_line_in_files(replace_line_files, dry_run=False):
    """
    #Single line replacement..
    """
    for (replace_str, replace_with, replace_where) in replace_line_files:
        replace_where = _check_mount_path(replace_where)
        mounted_filepath = os.path.join(mount_point, replace_where)
        sed_replace(replace_str, replace_with, mounted_filepath,
                    dry_run=dry_run)


def _remove_multiline_in_files(multiline_delete_files, dry_run=False):
    """
    #Remove EVERYTHING between these lines..
    """
    for (delete_from, delete_to, replace_where) in multiline_delete_files:
        replace_where = _check_mount_path(replace_where)
        mounted_filepath = os.path.join(mount_point, replace_where)
        sed_delete_multi(delete_from, delete_to, mounted_filepath,
                         dry_run=dry_run)


def _check_mount_path(self, filepath):
    if not filepath:
        return filepath
    if filepath.startswith('/'):
        filepath = filepath[1:]
    return filepath
