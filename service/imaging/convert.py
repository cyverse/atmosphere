from service.imaging.common import prepare_chroot_env,\
                                   remove_chroot_env,\
                                   get_latest_ramdisk,\
                                   rebuild_ramdisk,\
                                   check_distro

from service.imaging.common import append_line_in_files,\
                                   prepend_line_in_files,\
                                   remove_line_in_files,\
                                   replace_line_in_files,\
                                   remove_multiline_in_files

from service.imaging.common import run_command,\
                                   create_file

def xen_to_kvm(mounted_path):
    """
    Determine distro and convert from XEN to KVM
    """
    distro = check_distro(mounted_path)
    if 'CentOS' in distro:
        return xen_to_kvm_centos(mounted_path)
    elif 'Ubuntu' in distro:
        return xen_to_kvm_ubuntu(mounted_path)


def xen_to_kvm_ubuntu(mounted_path):
    """
    These operations must be run to convert an Ubuntu Machine from XEN-based
    virtualization to KVM-based virtualization
    """
    remove_line_file_list = [
            #("pattern_match", "file_to_test")
            ("atmo_boot",  "etc/rc.local"),
            ("sda2", "etc/fstab"),
            ("sda3",  "etc/fstab")]

    # Remove the Xen start-up script
    remove_file_list = [
            '/etc/init/hvc0.conf']

    #Add the KVM start-up script

    #Add the single line if the file exists
    append_line_file_list = [
            #("line to add", "file_to_append")
            ("exec /sbin/getty -L 38400 ttyS0 vt102", "etc/init/getty.conf"),
            ("exec /sbin/getty -L 38400 ttyS1 vt102", "etc/init/getty.conf"),
    ]
    #Create the whole file if it doesnt exist
    kvm_getty_script = """# getty - ttyS*
# This service maintains a getty on ttyS0/S1
# from the point the system is started until
# it is shut down again.

start on stopped rc RUNLEVEL=[2345]
stop on runlevel [!2345]

respawn
exec /sbin/getty -L 38400 ttyS0 vt102
exec /sbin/getty -L 38400 ttyS1 vt102
"""
    remove_line_in_files(remove_line_file_list, mounted_path)
    remove_files(remove_file_list, mounted_path)
    if not create_file("etc/init/getty.conf", mounted_path, kvm_getty_script):
        append_line_in_files(append_line_file_list, mounted_path)

def xen_to_kvm_centos(mounted_path):
    #replace \t w/ 4-space if this doesn't work so well..
    append_line_file_list = [
            #("line to add", "file_to_append")
            ("S0:2345:respawn:/sbin/agetty ttyS0 115200", "etc/inittab"),
            ("S1:2345:respawn:/sbin/agetty ttyS1 115200", "etc/inittab"),
    ]
    prepend_line_list = [
        ("LABEL=root\t\t/\t\t\text3\tdefaults,errors=remount-ro 0 0",
        "etc/fstab"),
        ]
    remove_line_file_list = [("alias scsi", "etc/modprobe.conf"),
                             ("atmo_boot", "etc/rc.local")]

    replace_line_file_list = [("^\/dev\/sda", "\#\/dev\/sda", "etc/fstab"),
                              ("^xvc0", "\#xvc0", "etc/inittab"),
                              ("xenblk", "ata_piix", "etc/modprobe.conf"),
                              ("xennet", "8139cp", "etc/modprobe.conf")]
    multiline_delete_files = [
        ("depmod -a","\/usr\/bin\/ruby \/usr\/sbin\/atmo_boot", "etc/rc.local"),
        ("depmod -a","\/usr\/bin\/ruby \/usr\/sbin\/atmo_boot", "etc/rc.d/rc.local")
    ]

    append_line_in_files(append_line_file_list, mounted_path)
    prepend_line_in_files(prepend_line_list, mounted_path)
    remove_line_in_files(remove_line_file_list, mounted_path)
    replace_line_in_files(replace_line_file_list, mounted_path)
    remove_multiline_in_files(multiline_delete_files, mounted_path)


    ### PREPARE CHROOT
    prepare_chroot_env(mounted_path)
    #Run this command in a prepared chroot
    run_command(["/usr/sbin/chroot", mounted_path, "/bin/bash", "-c",
                 "yum install -qy kernel mkinitrd grub"])
    remove_chroot_env(mounted_path)

    rebuild_ramdisk(mounted_path)
