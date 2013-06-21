import os

def make_image_bootable(self, image_path, mounted_path):
    """
    Call this function to make necessary changes for a bootable image
    """

    #First, label the disk image for /etc/fstab
    # label syntax: 
    # NOTE: This disk image should have the root partition
    run_command(['e2label', image_path, 'root'])
    distro = check_distro(mounted_path)
    if  distro == 'Ubuntu':
        xen_to_kvm_ubuntu(mounted_path)
    elif distro == 'CentOS':
        xen_to_kvm_centos(mounted_path)
    else:
        raise Exception("Cannot convert to distro: %s" % distro)

    #Ready for bootable-specific commands:

    #Uncomment to change the ethernet adapter for virtualbox
    #prepend_line_list = [
    #     ("alias eth0 e1000",
    #         "etc/modprobe.d/virtualbox"),
    #]
    #Touch to create..
    #open('etc/modprobe.d/virtualbox','a').close()
    #_prepend_line_in_files(prepend_line_list)

    #Uncomment to install sound card for virtualbox
    #append_line_list = [
    #    ("alias scsi_hostadapter1 ahci","etc/modprobe.d/modprobe.conf"),
    #    ("install pciehp /sbin/modprobe -q --ignore-install acpiphp;
    #    /bin/true","etc/modprobe.d/modprobe.conf"),
    #    ("alias snd-card-0 snd-intel8x0","etc/modprobe.d/modprobe.conf"),
    #    ("options snd-intel8x0 index=0","etc/modprobe.d/modprobe.conf"),
    #    ("options snd-card-0 index=0","etc/modprobe.d/modprobe.conf"),
    #    ("remove snd-intel8x0 { /usr/sbin/alsactl store 0 >/dev/null "
    #        "2>& 1 || : ; }; /sbin/modprobe -r --ignore-remove "
    #        "snd-intel8x0","etc/modprobe.d/modprobe.conf")
    #]
    #_append_line_in_files(append_line_list)

    #Uncomment to install a GUI
    ### PREPARE CHROOT

    #run_command(["/usr/sbin/chroot", mount_point, "/bin/bash", "-c", "yum "
    #"groupinstall -y \"X Window System\" \"GNOME Desktop Environment\""])

    ### Remove CHROOT
    #Uncomment to default to the GUI once the machine boots
    #replace_line_file_list = [
    #     (":[0-6]:initdefault",":5:initdefault",
    #         "etc/inittab"),
    #]
    #_replace_line_in_files(replace_line_file_list)

    _get_stage_files(mounted_path, distro)
    _rewrite_grub_conf(mounted_path)
    _install_grub(image_path)


def _install_grub(image_path):
    grub_stdin = """device (hd0) %s
geometry (hd0) %s %s %s
root (hd0,0)
setup (hd0)
quit""" % (image_path, disk['cylinders'], disk['heads'], disk['sectors'])
    run_command(
        ['grub', '--device-map=/dev/null', '--batch'], 
        stdin=grub_stdin)


def _get_stage_files(self, root_dir, distro):
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

    run_command(['/bin/bash','-c', 'cd %s/boot/grub/;ln -s grub.conf
    grub.cfg' % mount_point])
    run_command(['/bin/bash','-c', 'cd %s/boot/grub/;ln -s grub.conf
    menu.lst' % mount_point])
