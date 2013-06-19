from service.system_calls import run_command


##
# Tools
##
def get_latest_ramdisk(mounted_path):
    boot_dir = os.path.join(mounted_path,'boot/')
    output, _ = run_command(("/bin/bash", "-c", "ls -Fah /boot/"])
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



def mount_image(image_path, mount_point):
    if not check_dir(mount_point):
        os.makedirs(mount_point)
    _detect_and_mount_image(image_path, mount_point)


def create_empty_image(new_image_path, image_type='raw',
                      image_size_gb=5, bootable=False):
    run_command(['qemu-img','create','-f','%s' % image_type, new_image_path, "%sG" %
        image_size_gb])
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
    _format_partition(fdisk_stats['disk'], partition, new_image_path)
    return new_image_path


##
# Validation
##

def check_file(file_path):
    return os.path.isfile(file_path)


def check_dir(dir_path):
    return os.path.isdir(dir_path)


def check_mounted(mount_point):
    """
    Testing for mount: 
      1. Does the mountpoint exist?
      2. Is a filesystem mounted?
        * Does /bin/bash exist?
      OPT:
        * Check 'mount' for mount_point..
    """
    if not check_dir(mount_point):
        return False
    bashtest = os.path.isfile(
                   os.path.join(
                       mount_point,'bin/bash'))
    return bashtest


##
# Private Methods
##
def _grub_base_install(image_path, mounted_root):
    #Edit grub.conf
    #Move rc.local

    #Inject stage files
    _get_stage_files(mounted_root, check_distro(mounted_root))
    disk = fdisk_stats['disk']
    #SETUP GRUB
    grub_stdin = """device (hd0) %s
    geometry (hd0) %s %s %s
    root (hd0,0)
    setup (hd0)
    quit""" % (image_path,disk['cylinders'], disk['heads'],
            disk['sectors_per_track'])
    run_command(['grub', '--device-map=/dev/null', '--batch'], stdin=grub_stdin)


def check_distro(root_dir=''):
    """
    Either your CentOS or your Ubuntu.
    """
    etc_release_path = os.path.join(root_dir,'etc/*release*')
    (out,err) = run_command(['/bin/bash','-c',etc_release_path])
    if 'CentOS' in out:
        return 'CentOS'
    else:
        return 'Ubuntu'

def _get_stage_files(root_dir, distro):
    if distro == 'CentOS':
        run_command(['/bin/bash','-c','cp -f %s/extras/export/grub_files/centos/* %s/boot/grub/' % (settings.PROJECT_ROOT, root_dir)])
    elif distro == 'Ubuntu':
        run_command(['/bin/bash','-c','cp -f %s/extras/export/grub_files/ubuntu/* %s/boot/grub/' % (settings.PROJECT_ROOT, root_dir)])

def _format_partition(disk, part, image_path):
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

    #Then unmount it all
    run_command(['losetup', '-d', loop_dev])


def _losetup_extract_device(loop_str):
    return loop_str.split(' ')[-1].strip()


def _detect_and_mount_image(image_path, mount_point):
    file_name, file_ext= os.path.splitext(image_path)
    if file_ext == 'qcow':
        mount_qcow(image_path, mount_point)
        # nbd -c /dev/nbd* (Empty nbd test needed) /full/path/to/img
        # mount /dev/nbd*(p1) mount_point
    elif file_ext == 'raw' or file_ext == 'img':
        _mount_raw(image_path, mount_point)
    return True


def _remove_chroot_env(mount_point):
    proc_dir = os.path.join(mount_point,'proc/')
    sys_dir = os.path.join(mount_point,'sys/')
    dev_dir = os.path.join(mount_point,'dev/')
    run_command(['umount', proc_dir])
    run_command(['umount', sys_dir])
    run_command(['umount', dev_dir])


def _prepare_chroot_env(mount_point):
    proc_dir = os.path.join(mount_point,'proc/')
    sys_dir = os.path.join(mount_point,'sys/')
    dev_dir = os.path.join(mount_point,'dev/')
    run_command(['mount', '-t', 'proc', '/proc', proc_dir])
    run_command(['mount', '-t', 'sysfs', '/sys', sys_dir])
    run_command(['mount', '-o', 'bind', '/dev',  dev_dir])


def _mount_qcow(image_path, mount_point):
    nbd_dev = _get_next_nbd()
    #Mount disk to /dev/nbd*
    run_command(['qemu-nbd', '-c', nbd_dev, image_path])
    try:
        #Attempting to mount the file system partition
        partition = _fdisk_get_partition(nbd_dev)
        out, err = run_command(['mount', '%s' % partition['image_name'], mount_point])
        if err:
            raise Exception("Could not mount QCOW partiton: %s" % partition)
    except Exception:
        run_command(['qemu-nbd', '-d', nbd_dev])

    #The qcow image has been mounted
    return True


def _fdisk_get_partition(image_path):
    out, err = run_command(['fdisk','-l',image_path])
    fdisk_stats = _parse_fdisk_stats(out)
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


def _mount_raw(image_path, mount_point):
    out, err = run_command(['mount','-o','loop',image_path,mount_point])
    if 'specify the filesystem' in err:
        return _mount_raw_with_offsets(image_path, mount_point)
    #The raw image has been mounted
    return True

def _mount_raw_with_offsets(image_path, mount_point):
    partition = _fdisk_get_partition(image_path)
    offset = fdisk_stats['disk']['unit_byte_size'] * partition['start']
    out, err = run_command(['mount', '-o', 'loop,offset=%s' %  offset,
                             image_path, mount_point])
    if err:
        raise Exception("Could not auto-mount the RAW partition: %s" %
                partition)


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

    import re
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
        regex = re.compile("(?P<image_name>[\S]+)[ ]+(?P<bootable>[*]+)?[ ]+"
                           "(?P<start>[0-9]+)[ ]+(?P<end>[0-9]+)[ ]+"
                           "(?P<blocks>[0-9]+)[+]?[ ]+(?P<id>[0-9]+)[ ]+"
                           "(?P<system>[\S]+)")
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
