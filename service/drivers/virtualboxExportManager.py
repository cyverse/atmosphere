"""
ExportManager:
    Remote Eucalyptus Image management (euca2ools 1.3.1 + boto ec2)

Creating an Image from an Instance (Manual image requests)

>> from service.drivers.eucalyptusExportManager import ExportManager
>> manager = ExportManager()
>> manager.create_image('i-12345678', 'New image name v1')

>> os_manager.upload_euca_image('Migrate emi-F1F122E4', 
                                '/temp/image/path/name_of.img', 
                                '/temp/image/path/kernel/vmlinuz-...el5', 
                                '/temp/image/path/ramdisk/initrd-...el5.img')
"""

import getopt
import sys
import os
import glob
import subprocess
import time
from hashlib import md5

from datetime import datetime
from urlparse import urlparse
from xml.dom import minidom

from boto import connect_ec2
from boto.ec2.regioninfo import RegionInfo
from boto.ec2.instance import Instance
from boto.s3.connection import S3Connection, OrdinaryCallingFormat
from boto.exception import S3ResponseError, S3CreateError
from boto.s3.key import Key

from euca2ools import Euca2ool, FileValidationError, Util, ConnectionFailed

from atmosphere import settings
from atmosphere.logger import logger
from service.drivers.eucalyptusImageManager import ImageManager as EucaImageManager
from boto.resultset import ResultSet

class ExportManager():
    """
    Convienence class that holds the procedure needed to export Virtualbox
    to each of the supported clouds
    """
    image_manager = None
    def __init__(self):
        pass

    def _remove_ldap_and_vnc(local_img_path, mount_point):
            self._chroot_local_image(local_img_path, mount_point, [
                ['/bin/bash', '-c', 'echo n3wpa55 | passwd root --stdin'], #First, change the root password
                ['yum', 'remove', '-qy', 'openldap', 'realvnc-vnc-server'], #Then Remove ldap!
            ])
            self.run_command(['mount', '-o', 'loop', local_img_path, mount_point])
            self.run_command(['find', '%s' % mount_point, '-type', 'f', '-name', '*.rpmsave', '-exec', 'rm', '-f', '{}', ';'])
            self.run_command(['umount', mount_point])

    def _xen_migrations(self, image_path, mount_point):
        """
        Make any changes necessary to migrate a XEN-based VM to VirtualBox:
        * Remove everything from rc.local
        * Add modules to modprobe.conf
        * Update the kernel, the initrd tools, and grub
        * Change grub.conf line
        TODO:
        (This was already the case, so these changes were glossed over..
        * If NOT /dev/sda, convert /etc/fstab to /dev/sda (Even better: Use blkid and UUID or LABEL so the hard drive order doesnt matter)

        """
        #Prepare the paths
        if not os.path.exists(image_path):
            logger.error("Could not find local image!")
            raise Exception("Image file not found")

        if not os.path.exists(mount_point):
            os.makedirs(mount_point)
        #Mount the directory
        self.run_command(['mount', '-o', 'loop', image_path, mount_point])
        #Multi-line SED Replacement.. Equivilant of: DeleteFrom/,/DeleteTo / d <--Delete the regexp match
        #NOTE: DO NOT USE LEADING SLASH!!
        for (delete_from, delete_to, replace_where) in [("depmod -a","\/usr\/bin\/ruby \/usr\/sbin\/atmo_boot", "etc/rc.local"),
                                                        ("depmod -a","\/usr\/bin\/ruby \/usr\/sbin\/atmo_boot", "etc/rc.d/rc.local"),
                                                       ]:
            replace_file_path = os.path.join(mount_point,replace_where)
            if os.path.exists(replace_file_path):
                self.run_command(["/bin/sed", "-i", "/%s/,/%s/d" % (delete_from, delete_to), replace_file_path])
        #Prepare for chroot fun
        self.run_command(['mount', '-t', 'proc', '/proc', mount_point+"/proc/"])
        self.run_command(['mount', '-t', 'sysfs', '/sys', mount_point+"/sys/"])
        self.run_command(['mount', '-o', 'bind', '/dev', mount_point+"/dev/"])
        #Let the fun begin
        self.run_command(["/usr/sbin/chroot", mount_point, "/bin/bash", "-c", "yum install -y kernel mkinitrd grub"])
        (output,stder) = self.run_command(["/usr/sbin/chroot", mount_point, "/bin/bash", "-c", "ls -Fah /boot/"])
        latest_rmdisk = ''
        rmdisk_version = ''
        for line in output.split('\n'):
            if 'initrd' in line and 'xen' not in line:
                latest_rmdisk = line
                rmdisk_version = line.replace('.img','').replace('initrd-','')
        self.run_command(["/usr/sbin/chroot", mount_point, "/bin/bash", "-c", "mkinitrd --with virtio_pci --with virtio_ring --with virtio_blk --with virtio_net --with virtio_balloon --with virtio -f /boot/%s %s" % (latest_rmdisk, rmdisk_version)])
        #REPLACE OLD MODPROBE.CONF LINES
        for (replace_str, replace_with, replace_where) in [ 
                                                            ("xenblk","ata_piix","etc/modprobe.conf"),
                                                            ("xennet","e1000","etc/modprobe.conf") ]:
            replace_file_path = os.path.join(mount_point,replace_where)
            if os.path.exists(replace_file_path):
                self.run_command(["/bin/sed", "-i", "s/%s/%s/" % (replace_str, replace_with), replace_file_path])

        #APPEND NEW MODPROBE.CONF LINES
        for (append_line, append_file) in [ 
                                                            ("alias scsi_hostadapter1 ahci","etc/modprobe.conf"),
                                                            ("install pciehp /sbin/modprobe -q --ignore-install acpiphp; /bin/true","etc/modprobe.conf"),
                                                            ("alias snd-card-0 snd-intel8x0","etc/modprobe.conf"),
                                                            ("options snd-card-0 index=0","etc/modprobe.conf"),
                                                            ("options snd-intel8x0 index=0","etc/modprobe.conf"),
                                                            ("remove snd-intel8x0 { /usr/sbin/alsactl store 0 >/dev/null 2>&1 || : ; }; /sbin/modprobe -r --ignore-remove snd-intel8x0","etc/modprobe.conf")

                                          ]:
            append_file_path = os.path.join(mount_point,append_file)
            if os.path.exists(append_file_path):
                self.run_command(["/bin/sed", "-i", "$ a\\%s" % (append_line,), append_file_path])
        #REPLACE THE GRUB.CONF
        new_grub_conf = """default=0
timeout=3
splashimage=(hd0,0)/boot/grub/splash.xpm.gz
title Atmosphere VM (%s)
    root (hd0,0)
    kernel /boot/vmlinuz-%s root=/dev/sda1 ro rhgb
    initrd /boot/%s
""" % (rmdisk_version, rmdisk_version, latest_rmdisk)
        with open(os.path.join(mount_point,'boot/grub/grub.conf'), 'w') as grub_file:
            grub_file.write(new_grub_conf)
        manager.run_command(['/bin/bash','-c', 'cd %s/boot/grub/;ln -s grub.conf menu.lst' % mount_point])
        manager.run_command(['/bin/bash','-c', 'cd %s/boot/grub/;ln -s grub.conf grub.cfg' % mount_point])
        #Don't forget to unmount!
        self.run_command(['umount', mount_point+"/proc/"])
        self.run_command(['umount', mount_point+"/sys/"])
        self.run_command(['umount', mount_point+"/dev/"])
        self.run_command(['umount', mount_point])

    def eucalyptus(self, instance_id, export_type, download_dir='/tmp', local_raw_path=None, convert_img_path=None, no_upload=False):
        """
        Image manager initiated
        Grab the running instance
        Download it locally
        Run eucalyptus cleaning
        Run export-specific cleaning
        Determine size of the disk
        """
        self.image_manager = EucaImageManager()
        #Download and clean the image if it was not passed as a kwarg
        if not local_raw_path or not os.path.exists(local_raw_path):
            mount_point = os.path.join(download_dir,'mount/')
            local_img_path = self.image_manager.download_instance(download_dir, instance_id)
            self.image_manager._clean_local_image(local_img_path, mount_point)
            self._xen_migrations(local_img_path, mount_point)
            image_size = self._get_file_size_gb(local_img_path)
            local_raw_path = self._build_new_image(local_img_path, download_dir, image_size)

        #Convert the image if it was not passed as a kwarg
        if not convert_img_path or not os.path.exists(convert_img_path):
            #Figure out if were dealing with XEN based..
            convert_img_path = self._convert_local_image(local_raw_path, export_type)
        ##Get the hash of the converted file
        #md5sum = self._large_file_hash(convert_img_path)
        #if no_upload:
        #    return (md5sum, None)
        ##Archive/Compress/Send to S3
        #tarfile_name = convert_img_path+'.tar.gz'
        #_compress_file(tarfile_name, [convert_img_path])
        ##_export_to_s3(os.path.basename(tar_filename), tar_filename)
        ##return (md5sum, url)

    def _get_file_size_gb(self, filename):
        import math
        byte_size = os.path.getsize(filename)
        one_gb = 1024**3
        gb_size = math.ceil( float(byte_size)/one_gb )
        return int(gb_size)


    def _parse_fdisk_stats(self, output):
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
        import re
        line = output.split('\n')
        #Going line-by-line here.. Line 2
        regex = re.compile("(?P<heads>[0-9]+) heads, (?P<sectors>[0-9]+) sectors/track, (?P<cylinders>[0-9]+) cylinders, total (?P<total>[0-9]+) sectors")
        result = regex.search(line[2])
        result_map = result.groupdict()
        #Adding line 3
        regex = re.compile("(?P<unit>[0-9]+) bytes")
        result = regex.search(line[3])
        result_map.update(result.groupdict())
        #Adding line 4
        regex = re.compile("(?P<logical_sector_size>[0-9]+) bytes / (?P<physical_sector_size>[0-9]+) bytes")
        result = regex.search(line[4])
        result_map.update(result.groupdict())
        #
        regex = re.compile("(?P<start>[0-9]+)[ ]+(?P<end>[0-9]+)[ ]+(?P<blocks>[0-9]+)")
        result = regex.search(line[9])
        result_map.update(result.groupdict())
        #Regex saves the variables as strings, but they are more useful as ints
        for (k,v) in result_map.items():
            result_map[k] = int(v)
        return result_map

    def _build_new_image(self, original_image, download_dir, image_gb_size=10):
        #Create virtual Disk Image
        new_raw_img = original_image.replace('.img','.raw')
        one_gb = 1024
        total_size = one_gb*image_gb_size
        self.run_command(['qemu-img','create','-f','raw',new_raw_img, "%sG" % image_gb_size])
        #Add loopback device
        (loop_str, _) = self.run_command(['losetup','-fv', new_raw_img])
        loop_dev = loop_str.replace('Loop device is ','').strip()
        #Partition the device
        sfdisk_input = ",,L,*\n;\n;\n;\n"
        self.run_command(['sfdisk', '-D', loop_dev], stdin=sfdisk_input)
        (out, _) = self.run_command(['fdisk','-l', loop_dev])
        #Fun parsing the fdisk output!
        disk = self._parse_fdisk_stats(out)

        offset = disk['start']* disk['logical_sector_size']
        ##Calculating C/H/S using fdisk -l:
        #Skip to the sector listed in fdisk and setup a second loop device
        (offset_loop, _) = self.run_command(['losetup', '-fv', '-o', '%s' % offset, new_raw_img])
        offset_loop_dev = offset_loop.replace('Loop device is ','').strip()
        #Make the filesystem
        #4096 = Default block size on ext2/ext3
        block_size = 4096
        fs_size = ((disk['end'] - disk['start']) * disk['unit']) / block_size
        self.run_command(['mkfs.ext3', '-b', '%s' % block_size, offset_loop_dev, '%s' % fs_size])
        #Copy the Filesystem
        empty_raw_dir = os.path.join(download_dir, 'bootable_raw_here')
        orig_raw_dir = os.path.join(download_dir, 'original_img_here')
        self.run_command(['mkdir', '-p', empty_raw_dir])
        self.run_command(['mkdir', '-p', orig_raw_dir])
        self.run_command(['mount', '-t', 'ext3', offset_loop_dev, empty_raw_dir])
        self.run_command(['mount', '-t', 'ext3', original_image, orig_raw_dir])
        self.run_command(['rsync', '-a', '--inplace', '%s/*' % orig_raw_dir, empty_raw_dir])
        self.run_command(['umount', orig_raw_dir])
        #Edit grub.conf
        #Move rc.local

        #Inject stage files
        self._get_stage_files(empty_raw_dir, self._get_distro(empty_raw_dir))
        self.run_command(['umount', empty_raw_dir])
        self.run_command(['losetup','-d', loop_dev])
        self.run_command(['losetup','-d', offset_loop_dev])

        #SETUP GRUB
        grub_stdin = """device (hd0) %s
        geometry (hd0) %s %s %s
        root (hd0,0)
        setup (hd0)
        quit""" % (new_raw_img,disk['cylinders'], disk['heads'], disk['sectors'])
        self.run_command(['grub', '--device-map=/dev/null', '--batch'], stdin=grub_stdin)
        #Delete EVERYTHING
       
    def _get_stage_files(self, root_dir, distro):
        if distro == 'CentOS':
            self.run_command(['/bin/bash','-c','cp -f %s/extras/export/grub_files/centos/* %s/boot/grub/' % (settings.PROJECT_ROOT, root_dir)])
        elif distro == 'Ubuntu':
            self.run_command(['/bin/bash','-c','cp -f %s/extras/export/grub_files/ubuntu/* %s/boot/grub/' % (settings.PROJECT_ROOT, root_dir)])
 
    def _get_distro(self, root_dir=''):
        """
        Either your CentOS or your Ubuntu.
        """
        (out,err) = self.run_command(['/bin/bash','-c','cat %s/etc/*release*' % root_dir])
        if 'CentOS' in out:
            return 'CentOS'
        else:
            return 'Ubuntu'
        

    def _compress_file(tar_filename, files=[]):
        if not os.path.exists(tar_filename):
            self._tarzip_image(tar_filename, files)

    def _export_to_s3(keyname, the_file, bucketname='eucalyptus_exports'):
        key = self.image_manager._upload_file_to_s3(bucketname, keyname, the_file) #Key matches on basename of file
        url = key.generate_url(60*60*24*7) # 7 days from now.
        return url

    def _large_file_hash(self, file_path):
        logger.debug("Calculating MD5 Hash for %s" % file_path)
        md5_hash = md5()
        with open(file_path,'rb') as f:
            for chunk in iter(lambda: f.read(md5_hash.block_size * 128), b''): #b'' == Empty Byte String
                md5_hash.update(chunk)
        return md5_hash.hexdigest()
        #Confirm instance existence
        try:
            reservation = self.find_instance(instance_id)[0]
        except IndexError, no_instance:
            raise Exception("No Instance Found with ID %s" % instance_id)

        #Friendly names
        image_name = image_name.replace(' ','_').replace('/','-')

        #Collect information about instance to fill optional arguments
        owner = reservation.owner_id
        logger.info("Instance belongs to: %s" % owner)
        if not kernel:
            kernel = reservation.instances[0].kernel
        if not ramdisk:
            ramdisk = reservation.instances[0].ramdisk
        parent_emi = reservation.instances[0].image_id

        if not meta_name:
            #Format empty meta strings to match current iPlant imaging standard, if not given
            meta_name = '%s_%s_%s_%s' % ('admin',owner,image_name, datetime.now().strftime('%m%d%Y_%H%M%S'))
            image_path = '%s/%s.img' % (local_download_dir, meta_name )
        else:
            image_path = '%s/%s.img' % (local_download_dir, meta_name )

        if not remote_img_path:
            remote_img_path = '/usr/local/eucalyptus/%s/%s/root' % (owner, instance_id)

        ##Run sub-scripts to retrieve, mount and clean image, upload it, then remove it
        image_path = self._download_remote_image(instance_id, image_path, remote_img_path)
        self._clean_local_image(image_path, '%s/mount/' % local_download_dir, exclude=exclude)
        new_image_id = self._upload_local_image(image_path, kernel, ramdisk, local_download_dir, parent_emi, meta_name, image_name, public, private_user_list)
        if not keep_image:
            self._remove_local_image("%s/%s*" % (local_download_dir,meta_name))
        return new_image_id

    def _tarzip_image(self, tarfile_path, file_list):
        import tarfile
        tar = tarfile.open(tarfile_path, "w:gz")
        logger.debug("Creating tarfile:%s" % tarfile_path)
        for name in file_list:
            logger.debug("Tarring file:%s" % name)
            tar.add(name)
        tar.close()

    def _convert_local_image(self, local_img_path, conversion_type):
        if 'vmdk' in conversion_type:
            convert_img_path = local_img_path.replace('.img','.vmdk')
            self.run_command(['qemu-img', 'convert', local_img_path, '-O', 'vmdk', convert_img_path])
        elif 'vdi' in conversion_type:
            raw_img_path = local_img_path.replace('.img','.raw')
            #Convert to raw if its anything else..
            if '.raw' not in local_img_path:
                self.run_command(['qemu-img', 'convert', local_img_path, '-O', 'raw', raw_img_path])
            #Convert from raw to vdi
            convert_img_path = raw_img_path.replace('.raw', '.vdi')
            self.run_command(['VBoxManage', 'convertdd',raw_img_path, convert_img_path])
        else:
            convert_img_path = None
            logger.warn("Failed to export. Unknown type: %s" % (conversion_type,) )
        return convert_img_path

    def run_command(self, commandList, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=None):
        """
        Using Popen, run any command at the system level and record the output and error streams
        """
        out = None
        err = None
        logger.debug("Running Command:<%s>" % ' '.join(commandList))
        try:
            if stdin:
                proc = subprocess.Popen(commandList, stdout=stdout, stderr=stderr, stdin=subprocess.PIPE)
            else:
                proc = subprocess.Popen(commandList, stdout=stdout, stderr=stderr)
            out,err = proc.communicate(input=stdin)
        except Exception, e:
            logger.error(e)
        if stdin:
            logger.debug("STDIN: %s" % stdin)
        logger.debug("STDOUT: %s" % out)
        logger.debug("STDERR: %s" % err)
        return (out,err)

    def _chroot_local_image(self, image_path, mount_point, commands_list):
        #Prepare the paths
        if not os.path.exists(image_path):
            logger.error("Could not find local image!")
            raise Exception("Image file not found")

        if not os.path.exists(mount_point):
            os.makedirs(mount_point)
        #Mount the directory
        self.run_command(['mount', '-o', 'loop', image_path, mount_point])
        for commands in commands_list:
            command_list = ['chroot', mount_point]
            command_list.extend(commands)
            self.run_command(command_list)
        self.run_command(['umount', mount_point])
