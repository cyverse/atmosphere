import os
from service.imaging.common import check_distro
from service.imaging.convert import xen_to_kvm_ubuntu,\
                                    xen_to_kvm_centos
from service.imaging.common import rebuild_ramdisk, run_command,\
                                   get_latest_ramdisk, fdisk_image
from atmosphere import settings
#No.
#
#def make_image_bootable(mounted_path, image_path):
#    """
#    Call this function to make necessary changes for a bootable image
#    """
#
#    #First, label the disk image for /etc/fstab
#    # label syntax: 
#    # NOTE: This disk image should have the root partition
#    run_command(['e2label', image_path, 'root'])
#
#    distro = check_distro(mounted_path)
#    if  distro == 'Ubuntu':
#        xen_to_kvm_ubuntu(mounted_path)
#    elif distro == 'CentOS':
#        xen_to_kvm_centos(mounted_path)
#    else:
#        raise Exception("Cannot convert to distro: %s" % distro)
#    #Both conversions require change to ramdisk
#    rebuild_ramdisk(mounted_path)
#    add_grub(mounted_path, image_path)


def add_grub(mounted_path, image_path):
    """
    Defines the order of sub-functions needed to install
    grub onto a VM without the use of a LiveCD/Floppy/Existing Grub install
    """
    distro = check_distro(mounted_path)
    _get_stage_files(mounted_path, distro)
    _rewrite_grub_conf(mounted_path)
    _install_grub(image_path)


def _install_grub(image_path):
    fdisk_stats = fdisk_image(image_path)
    disk = fdisk_stats['disk']
    grub_stdin = """device (hd0) %s
geometry (hd0) %s %s %s
root (hd0,0)
setup (hd0)
quit""" % (image_path, disk['cylinders'], disk['heads'],
        disk['sectors_per_track'])
    run_command(
        ['grub', '--device-map=/dev/null', '--batch'], 
        stdin=grub_stdin)


def _get_stage_files(root_dir, distro):
    """
    Stage 1 is located in the MBR and mainly points to Stage 2, since the MBR
    is too small to contain all of the needed data.

    Stage 2 points to its configuration file, which contains all of the complex
    user interface and options we are normally familiar with when talking about
    GRUB. Stage 2 can be located anywhere on the disk. If Stage 2 cannot find
    its configuration table, GRUB will cease the boot sequence and present the
    user with a command line for manual configuration.

    Stage 1.5 also exists and might be used if the boot information is small
    enough to fit in the area immediately after MBR.
    """
    if distro == 'CentOS':
        run_command(['/bin/bash','-c','cp -f %s/extras/export/grub_files/centos/* %s/boot/grub/' % (settings.PROJECT_ROOT, root_dir)])
    elif distro == 'Ubuntu':
        run_command(['/bin/bash','-c','cp -f %s/extras/export/grub_files/ubuntu/* %s/boot/grub/' % (settings.PROJECT_ROOT, root_dir)])

def _rewrite_grub_conf(mount_point):

    latest_rmdisk, rmdisk_version = get_latest_ramdisk(mount_point)

    new_grub_conf = """default=0
timeout=3
splashimage=(hd0,0)/boot/grub/splash.xpm.gz
title Atmosphere VM (%s)
    root (hd0,0)
    kernel /boot/vmlinuz-%s root=/dev/sda1 ro enforcing=0
    initrd /boot/%s
""" % (rmdisk_version, rmdisk_version, latest_rmdisk)

    with open(os.path.join(
            mount_point,'boot/grub/grub.conf'), 'w') as grub_file:
        grub_file.write(new_grub_conf)

    run_command(['/bin/bash','-c', 'cd %s/boot/grub/;ln -s grub.conf grub.cfg'
                 % mount_point])
    run_command(['/bin/bash','-c', 'cd %s/boot/grub/;ln -s grub.conf menu.lst'
                 % mount_point])
