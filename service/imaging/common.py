import glob
import os
import re
import subprocess

from threepio import logger

##
# Tools
##

def run_command(commandList, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                stdin=None, dry_run=False, shell=False):
    """
    NOTE: Use this to run ANY system command, because its wrapped around a loggger
    Using Popen, run any command at the system level and record the output and error streams
    """
    out = None
    err = None
    cmd_str = ' '.join(commandList)
    if dry_run:
        #Bail before making the call
        logger.debug("Mock Command: %s" % cmd_str)
        return ('','')
    try:
        if stdin:
            proc = subprocess.Popen(commandList, stdout=stdout, stderr=stderr,
                    stdin=subprocess.PIPE, shell=shell)
        else:
            proc = subprocess.Popen(commandList, stdout=stdout, stderr=stderr,
                    shell=shell)
        out,err = proc.communicate(input=stdin)
    except Exception, e:
        logger.exception(e)
    if stdin:
        logger.debug("%s STDIN: %s" % (cmd_str, stdin))
    logger.debug("%s STDOUT: %s" % (cmd_str, out))
    logger.debug("%s STDERR: %s" % (cmd_str, err))
    return (out,err)


def overwrite_file(filepath, dry_run=False):
    if not os.path.exists(filepath):
        logger.warn("Cannot copy /dev/null to non-existent file: %s" %
                filepath)
        return
    cmd_list = ['/bin/cp', '-f', '/dev/null', '%s' % filepath]
    run_command(cmd_list, dry_run=dry_run)


def create_file(filepath, mount_point, text_to_write, dry_run=False):
    filepath = _check_mount_path(filepath)
    create_file_path = os.path.join(mount_point, filepath)
    if  os.path.exists(create_file_path):
        logger.warn("Cannot create file %s, the file already exists."
                    % create_file_path)
        return False
    with open(create_file_path, 'w') as the_file:
        #Write the text, end with empty line
        the_file.write('%s\n' % text_to_write)
    return True


def wildcard_remove(wildcard_path, dry_run=False):
    """
    Expand the wildcard to match all files, delete each one.
    """
    logger.debug("Wildcard remove: %s" % wildcard_path)
    glob_list = glob.glob(wildcard_path)
    if glob_list:
        for filename in glob_list:
            cmd_list = ['/bin/rm', '-rf', filename]
            run_command(cmd_list, dry_run=dry_run)

"""
SED tools - in-place editing of files on the system
BE VERY CAREFUL USING THESE -- YOU HAVE BEEN WARNED!
"""
def sed_delete_multi(from_here,to_here,filepath, dry_run=False):
    if not os.path.exists(filepath):
        logger.info("File not found: %s Cannot delete lines" % filepath)
        return
    cmd_list = ["/bin/sed", "-i", "/%s/,/%s/d" % (from_here, to_here),
                filepath]
    run_command(cmd_list, dry_run=dry_run)

def sed_replace(find,replace,filepath, dry_run=False):
    if not os.path.exists(filepath):
        logger.info("File not found: %s Cannot replace lines" % filepath)
        return
    cmd_list = ["/bin/sed", "-i", "s/%s/%s/" % (find,replace), filepath]
    run_command(cmd_list, dry_run=dry_run)

def sed_delete_one(remove_string, filepath, dry_run=False):
    if not os.path.exists(filepath):
        logger.info("File not found: %s Cannot delete lines" % filepath)
        return
    cmd_list = ["/bin/sed", "-i", "/%s/d" % remove_string, filepath]
    run_command(cmd_list, dry_run=dry_run)

def sed_append(append_string, filepath, dry_run=False):
    if not os.path.exists(filepath):
        logger.info("File not found: %s Cannot append lines" % filepath)
        return
    if _line_exists_in_file(append_string, filepath):
        return
    cmd_list = ["/bin/sed", "-i", "$ a\\%s" % append_string, filepath]
    run_command(cmd_list, dry_run=dry_run)

def sed_prepend(prepend_string, filepath, dry_run=False):
    if not os.path.exists(filepath):
        logger.info("File not found: %s Cannot prepend lines" % filepath)
        return
    if _line_exists_in_file(prepend_string, filepath):
        return
    cmd_list = ["/bin/sed", "-i", "1i %s" % prepend_string, filepath]
    run_command(cmd_list, dry_run=dry_run)

def _line_exists_in_file(needle, filepath):
    with open(filepath,'r') as _file:
        if [line for line in _file.readlines()
            if needle.strip() == line.strip()]:
            return True
    return False

   
def _mkinitrd_command(latest_rmdisk, rmdisk_version, preload=[], include=[]):
    preload.extend(['ahci'])
    include.extend(['virtio_pci', 'virtio_ring',
                    'virtio_blk', 'virtio_net',
                    'virtio_balloon', 'virtio'])

    mkinitrd_str = "mkinitrd"
    for module in preload:
        mkinitrd_str += " --preload %s" % module
    for module in include:
        mkinitrd_str += " --with %s" % module
    mkinitrd_str += " -f /boot/%s %s" % (latest_rmdisk, rmdisk_version)
    return mkinitrd_str

def rebuild_ramdisk(mounted_path, preload=[], include=[]):
    """
    This function will get more complicated in the future... We will need to
    support opts in mkinitrd, etc.
    """

    #Run this command after installing the latest (non-xen) kernel
    latest_rmdisk, rmdisk_version = get_latest_ramdisk(mounted_path)
    mkinitrd_str = _mkinitrd_command(latest_rmdisk, rmdisk_version,
                                     preload=preload, include=include)
    try:
        prepare_chroot_env(mounted_path)
        #Create a brand new ramdisk using the KVM variables set above
        run_command(["/usr/sbin/chroot", mounted_path,
                     "/bin/bash", "-c", mkinitrd_str])
    finally:
        remove_chroot_env(mounted_path)


def get_latest_ramdisk(mounted_path):
    boot_dir = os.path.join(mounted_path,'boot/')
    output, _ = run_command(["/bin/bash", "-c", "ls -Fah %s" % boot_dir])
    #Determine the latest (KVM) ramdisk to use
    latest_rmdisk = ''
    rmdisk_version = ''
    for line in output.split('\n'):
        if 'initrd' in line and 'xen' not in line:
            latest_rmdisk = line
            rmdisk_version = line.replace('.img','').replace('initrd-','')
    if not latest_rmdisk or not rmdisk_version:
        raise Exception("Could not determine the latest ramdisk. Is the "
                        "ramdisk located in %s?" % boot_dir)
    return latest_rmdisk, rmdisk_version


def copy_disk(old_image, new_image, download_dir):
    old_img_dir = os.path.join(download_dir, 'old_image')
    new_img_dir  = os.path.join(download_dir, 'new_image')
    run_command(['mkdir', '-p', old_img_dir])
    run_command(['mkdir', '-p', new_img_dir])
    try:
        mount_image(old_image, old_img_dir)
        mount_image(new_image, new_img_dir)

        run_command(['/bin/bash', '-c', 'rsync --inplace -a %s/* %s'
                     % (old_img_dir, new_img_dir)])
    finally:
        run_command(['umount', old_img_dir])
        run_command(['umount', new_img_dir])
    ##TODO: Delete the directories
    #old_img_dir)
    #new_img_dir)



def mount_image(image_path, mount_point):
    if not check_dir(mount_point):
        os.makedirs(mount_point)
    return _detect_and_mount_image(image_path, mount_point)


def create_empty_image(new_image_path, image_type='raw',
                      image_size_gb=5, bootable=False, label='root'):
    run_command(['qemu-img', 'create', '-f', image_type,
                 new_image_path, "%sG" % image_size_gb])

    #SFDisk script by stdin
    #See http://linuxgazette.net/issue46/nielsen.html#create
    if bootable:
        line_one = ",,L,*\n"
    else:
        line_one = ",,L,\n"
    sfdisk_input = "%s;\n;\n;\n" % line_one
    run_command(['sfdisk', '-D', new_image_path], stdin=sfdisk_input)
    #Disk has unformatted partition
    out, err = run_command(['fdisk','-l',new_image_path])
    fdisk_stats = _parse_fdisk_stats(out)
    partition = _select_partition(fdisk_stats['devices'])
    _format_partition(fdisk_stats['disk'], partition, new_image_path,
            label=label)
    return new_image_path


##
# Validation
##

def check_file(file_path):
    return os.path.isfile(file_path)


def check_dir(dir_path):
    return os.path.isdir(dir_path)


##
# Private Methods
##

def append_line_in_files(append_files, mount_point, dry_run=False):
    for (append_line, append_to) in append_files:
        append_to = _check_mount_path(append_to)
        mounted_filepath = os.path.join(mount_point, append_to)
        sed_append(append_line, mounted_filepath, dry_run=dry_run)

def prepend_line_in_files(prepend_files, mount_point, dry_run=False):
    for (prepend_line, prepend_to) in prepend_files:
        prepend_to = _check_mount_path(prepend_to)
        mounted_filepath = os.path.join(mount_point, prepend_to)
        sed_prepend(prepend_line, mounted_filepath, dry_run=dry_run)



def remove_files(rm_files, mount_point, dry_run=False):
    """
    #Removes file (Matches wildcards)
    """
    for rm_file in rm_files:
        rm_file = _check_mount_path(rm_file)
        rm_file_path = os.path.join(mount_point, rm_file)
        wildcard_remove(rm_file_path, dry_run=dry_run)


def overwrite_files(overwrite_files, mount_point, dry_run=False):
    """
    #Copy /dev/null to clear sensitive logging data
    """
    for overwrite_path in overwrite_files:
        overwrite_path = _check_mount_path(overwrite_path)
        overwrite_file_path = os.path.join(mount_point, overwrite_path)
        overwrite_file(overwrite_file_path, dry_run=dry_run)


def remove_line_in_files(remove_line_files, mount_point, dry_run=False):
    """
    #Single line removal..
    """
    for (remove_line_w_str, remove_from) in remove_line_files:
        remove_from = _check_mount_path(remove_from)
        mounted_filepath = os.path.join(mount_point, remove_from)
        sed_delete_one(remove_line_w_str, mounted_filepath, dry_run=dry_run)


def replace_line_in_files(replace_line_files, mount_point, dry_run=False):
    """
    #Single line replacement..
    """
    for (replace_str, replace_with, replace_where) in replace_line_files:
        replace_where = _check_mount_path(replace_where)
        mounted_filepath = os.path.join(mount_point, replace_where)
        sed_replace(replace_str, replace_with, mounted_filepath,
                    dry_run=dry_run)


def remove_multiline_in_files(multiline_delete_files, mount_point, dry_run=False):
    """
    #Remove EVERYTHING between these lines..
    """
    for (delete_from, delete_to, replace_where) in multiline_delete_files:
        replace_where = _check_mount_path(replace_where)
        mounted_filepath = os.path.join(mount_point, replace_where)
        sed_delete_multi(delete_from, delete_to, mounted_filepath,
                         dry_run=dry_run)


def _check_mount_path(filepath):
    if not filepath:
        return filepath
    if filepath.startswith('/'):
        filepath = filepath[1:]
    return filepath


def check_distro(root_dir=''):
    """
    Either your CentOS or your Ubuntu.
    """
    etc_release_path = os.path.join(root_dir,'etc/*release*')
    (out,err) = run_command(['/bin/bash','-c','cat %s' % etc_release_path])
    if 'CentOS' in out:
        return 'CentOS'
    else:
        return 'Ubuntu'

def _get_stage_files(root_dir, distro):
    if distro == 'CentOS':
        run_command(['/bin/bash','-c','cp -f %s/extras/export/grub_files/centos/* %s/boot/grub/' % (settings.PROJECT_ROOT, root_dir)])
    elif distro == 'Ubuntu':
        run_command(['/bin/bash','-c','cp -f %s/extras/export/grub_files/ubuntu/* %s/boot/grub/' % (settings.PROJECT_ROOT, root_dir)])

def _format_partition(disk, part, image_path, label=None):
    #This is a 'known constant'.. It should never change..
    #4096 = Default block size for ext2/ext3
    BLOCK_SIZE = 4096

    #First mount the loopback device
    loop_offset = part['start'] * disk['logical_sector_size']
    (loop_str, _) = run_command(['losetup', '-fv', '-o', '%s' % loop_offset,
        image_path])

    #The last word of the output is the device
    loop_dev = _losetup_extract_device(loop_str)
    #loop_dev == /dev/loop*
    
    #Then mkfs
    unit_length = part['end'] - part['start']
    fs_size = unit_length * disk['unit_byte_size'] / BLOCK_SIZE
    run_command(['mkfs.ext3', '-b', '%s' % BLOCK_SIZE, loop_dev])
    if label:
        run_command(['e2label', loop_dev, label])
    #Then unmount it all
    run_command(['losetup', '-d', loop_dev])


def _losetup_extract_device(loop_str):
    return loop_str.split(' ')[-1].strip()


def _detect_and_mount_image(image_path, mount_point):
    file_name, file_ext= os.path.splitext(image_path)
    if file_ext == '.qcow' or file_ext == '.qcow2':
        return mount_qcow(image_path, mount_point)
    elif file_ext == '.raw' or file_ext == '.img':
        return mount_raw(image_path, mount_point)
    raise Exception("Encountered an unknown image type -- Extension : %s" %
            file_ext)

def check_mounted(mount_point):
    dev_location = None
    #Drop trailing slash to match 'mount' syntax
    if mount_point and mount_point.endswith('/'):
        mount_point = mount_point[:-1]
    #Run mount and scan the output for 'mount_point'
    stdout, stderr = run_command(['mount'])
    regex = re.compile("(?P<device>[\w/]+) on (?P<location>.*) type")
    for line in stdout.split('\n'):
        res = regex.search(line)
        if not res:
            continue
        search_dict = res.groupdict()
        mount_location = search_dict['location']
        if mount_point == mount_location:
            dev_location = search_dict['device']

    return dev_location

def unmount_image(image_path, mount_point):
    device = check_mounted(mount_point)
    if not device:
        return ('', '%s is not mounted' % image_path)
    #Check extension to determine how to unmount
    file_name, file_ext= os.path.splitext(image_path)
    if file_ext == '.qcow' or file_ext == '.qcow2':
        return unmount_qcow(device)
    elif file_ext == '.raw' or file_ext == '.img':
        return unmount_raw(device)
    raise Exception("Encountered an unknown image type -- Extension : %s" %
            file_ext)

def unmount_raw(block_device):
    #Remove net block device
    out, err = run_command(['umount', block_device])
    if err:
        return out, err

def unmount_qcow(nbd_device):
    #Remove net block device
    out, err = run_command(['umount', nbd_device])
    if err:
        return out, err
    out, err = run_command(['qemu-nbd', '-d', nbd_device])
    if err:
        return out, err

def remove_chroot_env(mount_point):
    proc_dir = os.path.join(mount_point,'proc/')
    sys_dir = os.path.join(mount_point,'sys/')
    dev_dir = os.path.join(mount_point,'dev/')
    etc_resolv_file = os.path.join(mount_point,'etc/resolv.conf')
    run_command(['umount', proc_dir])
    run_command(['umount', sys_dir])
    run_command(['umount', dev_dir])
    run_command(['umount', etc_resolv_file])


def prepare_chroot_env(mount_point):
    proc_dir = os.path.join(mount_point,'proc/')
    sys_dir = os.path.join(mount_point,'sys/')
    dev_dir = os.path.join(mount_point,'dev/')
    etc_resolv_file = os.path.join(mount_point,'etc/resolv.conf')
    run_command(['mount', '-t', 'proc', '/proc', proc_dir])
    run_command(['mount', '-t', 'sysfs', '/sys', sys_dir])
    run_command(['mount', '-o', 'bind', '/dev',  dev_dir])
    run_command(['mount', '--bind', '/etc/resolv.conf', etc_resolv_file])

def fsck_qcow(image_path):
    if 'qcow' not in image_path:
        return
    nbd_dev = _get_next_nbd()
    run_command(['qemu-nbd', '-c', nbd_dev, image_path])
    run_command(['fsck', '-y', nbd_dev])
    run_command(['qemu-nbd', '-d', nbd_dev])

def mount_qcow(image_path, mount_point):
    nbd_dev = _get_next_nbd()
    #Mount disk to /dev/nbd*
    run_command(['qemu-nbd', '-c', nbd_dev, image_path])
    #Check if filesystem has multiple partitions
    try:
        partition = _fdisk_get_partition(nbd_dev)
        mount_from = partition['image_name']
    except Exception:
        mount_from = nbd_dev
    try:
        out, err = run_command(['mount', mount_from, mount_point])
        if err:
            raise Exception("Failed to mount QCOW. STDERR: %s" % err)
        #The qcow image has been mounted
        return out, err
    except Exception:
        run_command(['qemu-nbd', '-d', nbd_dev])
        logger.exception('Failed to mount QCOW')
        return '', 'Could not mount QCOW image:%s to device:%s' % (image_path, nbd_dev)


def fdisk_image(image_path):
    out, err = run_command(['fdisk','-l',image_path])
    fdisk_stats = _parse_fdisk_stats(out)
    return fdisk_stats


def _fdisk_get_partition(image_path):
    fdisk_stats = fdisk_image(image_path)
    partition = _select_partition(fdisk_stats['devices'])
    return partition

def _get_next_nbd():
    nbd_name = '/dev/nbd'
    nbd_count = 1
    MAX_PART = 16
    while nbd_count < MAX_PART:
        out, err = run_command(['fdisk','-l','%s%s' % (nbd_name, nbd_count)])
        if not out:
            #No output means the nbd is empty, ready for use.
            return '%s%s' % (nbd_name, nbd_count)
        nbd_count += 1
    raise Exception("Error: All /dev/nbd* devices are in use")


def mount_raw(image_path, mount_point):
    out, err = run_command(['mount','-o','loop',image_path,mount_point])
    logger.debug("Mount Output:%s\nMount Error:%s" % (out, err))
    if 'specify the filesystem' in err:
        return mount_raw_with_offsets(image_path, mount_point)
    elif 'already mounted' in err and mount_point in err:
        #Already mounted in this location. Everything is fine.
        return '', ''

    #Return output/error from the mount
    return out, err

def mount_raw_with_offsets(image_path, mount_point):
    fdisk_stats = fdisk_image(image_path)
    partition = _select_partition(fdisk_stats['devices'])
    offset = fdisk_stats['disk']['unit_byte_size'] * partition['start']
    out, err = run_command(['mount', '-o', 'loop,offset=%s' %  offset,
                             image_path, mount_point])
    if err:
        raise Exception("Could not auto-mount the RAW partition: %s" %
                partition)
    return out, err

def prepare_losetup(image_path):
    out, err = run_command(['fdisk','-l',image_path])
    fdisk_stats = _parse_fdisk_stats(out)
    partition = _select_partition(fdisk_stats['devices'])
    #This is a 'known constant'.. It should never change..
    #4096 = Default block size for ext2/ext3
    BLOCK_SIZE = 4096

    #First mount the loopback device
    loop_offset = part['start'] * disk['logical_sector_size']
    (loop_str, _) = run_command(['losetup', '-fv', '-o', '%s' % loop_offset,
        image_path])

    #The last word of the output is the device
    loop_dev = _losetup_extract_device(loop_str)
    return loop_dev

def _mount_lvm(image_path, mount_point):
    """
    LVM's are one of the more difficult problems..
    We will save this until it becomes necessary.. And it will.
    """
    #vgscan
    #...
    pass


def _select_partition(partitions):
    """
    TODO: Is there a way to pick the 'real' device out of the list?
    Ideas: 
      System == 'Linux'
      Select if bootable
    """
    if not partitions:
        return None
    partition = partitions[0]
    return partition


def _parse_fdisk_stats(output):
    """
    Until I find a better way, the best thing to do is parse through fdisk
    to get the important statistics aboutput the disk image

    Sample Input:
    (0, '')
    (1, 'Disk /dev/loop0: 9663 MB, 9663676416 bytes')
    (2, '255 heads, 63 sectors/track, 1174 cylinders, total 18874368 sectors')
    (3, 'Units = sectors of 1 * 512 = 512 bytes')
    (4, 'Sector size (logical/physical): 512 bytes / 512 bytes')
    (5, 'I/O size (minimum/optimal): 512 bytes / 512 bytes')
    (6, 'Disk identifier: 0x00000000')
    (7, '')
    (8, '      Device Boot      Start         End      Blocks   Id  System')
    (9, '/dev/loop0p1   *          63    18860309     9430123+  83  Linux')
    (10, '')
    Returns:
        A dictionary of string to int values for the disk:
        *heads, sectors, cylinders, sector_count, units, Sector Size, Start, End
    """


    DEVICE_LINE = 9

    if not output:
        return {}

    lines = output.split('\n')
    #Going line-by-line here.. Line 2
    disk_map = {}
    regex = re.compile(
        "(?P<heads>[0-9]+) heads, "
        "(?P<sectors_per_track>[0-9]+) sectors/track, "
        "(?P<cylinders>[0-9]+) cylinders, "
        "total (?P<sectors_total>[0-9]+) sectors")
    r = regex.search(lines[2])
    disk_map.update(r.groupdict())
    #Adding line 3
    regex = re.compile("(?P<unit_byte_size>[0-9]+) bytes")
    r = regex.search(lines[3])
    disk_map.update(r.groupdict())
    #Adding line 4
    regex = re.compile("(?P<logical_sector_size>[0-9]+) bytes / (?P<physical_sector_size>[0-9]+) bytes")
    r = regex.search(lines[4])
    disk_map.update(r.groupdict())
    ## Map each device partition
    devices = []
    while len(lines) > DEVICE_LINE:
        #TODO: For each partition, capture this input.. Also add optional
        # bootable flag
        regex = re.compile("(?P<image_name>[\S]+)\s+(?P<bootable>[*]+)?\s+"
                           "(?P<start>[0-9]+)\s+(?P<end>[0-9]+)\s+"
                           "(?P<blocks>[0-9]+)[+]?\s+(?P<id>\w+)\s+"
                           "(?P<system>.*)")
        r = regex.search(lines[DEVICE_LINE])
        #Ignore the empty lines
        if r:
            device_stats = r.groupdict()
            if not device_stats.get('image_name'):
                raise Exception("Regex failed to properly identify fdisk image. "
                                "This problem must be fixed by hand!")
            devices.append(device_stats)
        DEVICE_LINE += 1
    #Wrap-it-up
    fdisk_stats = {}
    _map_str_to_int(disk_map)
    [_map_str_to_int(dev) for dev in devices]
    fdisk_stats.update({'disk':disk_map})
    fdisk_stats.update({'devices':devices})
    return fdisk_stats


def _map_str_to_int(dictionary):
    """
    Regex saves the variables as strings, 
    but they are more useful as ints
    """
    for (k,v) in dictionary.items():
        if type(v) == str and v.isdigit():
            dictionary[k] = int(v)
    return dictionary
