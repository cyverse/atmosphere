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

    def _xen_migrations(image_path, mount_point):
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
        for (delete_from, delete_to, replace_where) in [("depmod -a","\/usr\/bin\/ruby \/usr\/sbin\/atmo_boot", "etc/rc.local")
                                                       ]:
            replace_file_path = os.path.join(mount_point,replace_where)
            if os.path.exists(replace_file_path):
                self.run_command(["/bin/sed", "-i", "/%s/,/%s/d" % (delete_from, delete_to), replace_file_path])
        #REPLACE OLD MODPROBE.CONF LINES
        for (replace_str, replace_with, replace_where) in [ 
                                                            ("console=xvc0","","boot/grub/grub.conf"),
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
        
        #Prepare for chroot fun
        self.run_command(['mount', '-t', 'proc', '/proc', mount_point+"/proc/"])
        self.run_command(['mount', '-t', 'sysfs', '/sys', mount_point+"/sys/"])
        self.run_command(['mount', '-o', 'bind', '/dev', mount_point+"/dev/"])
        #Let the fun begin
        self.run_command(["/usr/sbin/chroot", mount_point, "/bin/bash", "-c", "yum install -y kernel mkinitrd grub"])
        (output,stder) = self.run_command(["/usr/sbin/chroot", mount_point, "/bin/bash", "-c", "ls -Fah %s" % mount_point+"/boot/"])
        latest_kernel = ''
        kernel_version = ''
        for line in output:
            if 'initrd' in line and not 'xen' in line:
                latest_kernel = line
                kernel_version = line.replace('.img','').replace('initrd-','')
        self.run_command(["/usr/sbin/chroot", mount_point, "/bin/bash", "-c", "mkinitrd --with virtio_pci --with virtio_ring --with virtio_blk --with virtio_net --with virtio_balloon --with virtio -f /boot/%s %s" % (latest_kernel, kernel_version)])
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
        #Download and clean the image if it was not passed as a kwarg
        if not local_raw_path or not os.path.exists(local_raw_path):
            mount_point = os.path.join(download_dir,'mount/')
            local_img_path = self.image_manager.download_instance(download_dir, instance_id)
            self.image_manager._clean_local_image(local_img_path, mount_point)
            self._xen_migrations(local_img_path, mount_point)
            image_size = self._get_file_size_gb(local_img_path)
            local_raw_path = _build_new_image(local_img_path, download_dir, image_size)

        #Convert the image if it was not passed as a kwarg
        if not convert_img_path or not os.path.exists(convert_img_path):
            #Figure out if were dealing with XEN based..
            convert_img_path = self._convert_local_image(local_img_path, export_type)
        #Get the hash of the converted file
        md5sum = self._large_file_hash(convert_img_path)
        if no_upload:
            return (md5sum, None)
        #Archive/Compress/Send to S3
        tarfile_name = convert_img_path+'.tar.gz'
        _compress_file(tarfile_name, [convert_img_path])
        #_export_to_s3(os.path.basename(tar_filename), tar_filename)
        #return (md5sum, url)

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
        loop_dev = loop_str.replace('Loop device is ','')
        #Partition the device
        sfdisk_input = ",,L,*\n;\n;\n;\n"
        self.run_command(['sfdisk', '-D', loop_dev], stdin=sfdisk_input)
        (out, _) = self.run_command(['fdisk','-l', loop_dev])
        #Fun parsing the fdisk output!
        disk = self._parse_fdisk_stats(out)

        offset = disk['start']* disk['logical_sector_size']
        ##Calculating C/H/S using fdisk -l:
        #Skip to the sector listed in fdisk and setup a second loop device
        (offset_loop, _) = self.run_command(['losetup', '-fv', '-o', offset, original_image])
        offset_loop_dev = offset_loop.replace('Loop device is ','').strip()
        #Make the filesystem
        #4096 = Default block size on ext2/ext3
        block_size = 4096
        fs_size = ((disk['end'] - disk['start']) * disk['unit']) / block_size
        self.run_command(['mkfs.ext3', '-b', block_size, offser_loop_dev, fs_size])
        #Copy the Filesystem
        empty_raw_dir = os.path.join(download_dir, 'bootable_raw_here')
        orig_raw_dir = os.path.join(download_dir, 'original_img_here')
        self.run_command(['mkdir', '-p', empty_raw_dir])
        self.run_command(['mkdir', '-p', orig_raw_dir])
        self.run_command(['mount', '-t', 'ext3', loop_dev1, empty_raw_dir])
        self.run_command(['mount', '-t', 'ext3', original_image, orig_raw_dir])
        self.run_command(['/bin/bash', '-c', 'cp -a %s/* %s' % (orig_raw_dir, empty_raw_dir)])
        self.run_command(['umount', orig_raw_dir])
        #Edit grub.conf
        #Move rc.local
        #Inject stage files
        self._get_stage_files(empty_raw_dir, self._get_distro(orig_raw_dir))
        self.run_command(['umount', empty_raw_dir])
        #grub --device-map=/dev/null
        #grub> device (hd0) newimage.raw
        #grub> geometry (hd0) 1305 255 63
        #grub> root (hd0,0)
        #grub> setup (hd0)
        self.run_command(['losetup','-d', loop_dev])
        self.run_command(['losetup','-d', loop_dev1])
        self.run_command(['losetup','-d', loop_dev2])
        #Delete EVERYTHING
       
    def _get_stage_files(root_dir, distro):
        if distro == 'CentOS':
            self.run_command(['/bin/bash','-c','cp -f %s/extras/export/grub_giles/centos/* %s/boot/grub/' % (settings.PROJECT_ROOT, root_dir)])
        elif distro == 'Ubuntu':
            self.run_command(['/bin/bash','-c','cp -f %s/extras/export/grub_files/ubuntu/* %s/boot/grub/' % (settings.PROJECT_ROOT, root_dir)])
 
    def _get_distro(root_dir=''):
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
        key = self._upload_file_to_s3(bucketname, keyname, the_file) #Key matches on basename of file
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

    def download_image(self, download_dir, image_id):
        """
        Download an existing image to local download directory
        Required Args:
            download_dir - The directory the image will be saved to (/path/to/dir/)
            image_id - The image ID to be downloaded (eki-12341234, emi-12345678, eri-11111111)
        """
        download_dir = os.path.join(download_dir,image_id)
        part_dir = os.path.join(download_dir,'parts')

        for dir_path in [part_dir]:
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)

        machine = self.get_image(image_id)
        if not machine:
            raise Exception("Machine Not Found.")

        image_location = machine.location

        logger.debug("Complete. Begin Download of Image  @ %s.." % datetime.now())
        whole_image = self._retrieve_euca_image(image_location, download_dir, part_dir)[0]
        logger.debug("Complete @ %s.." % datetime.now())

        #Return path to image
        return os.path.join(download_dir,whole_image)

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
            convert_img_path = local_img_path.replace('.img', '.vdi')
            self.run_command(['qemu-img', 'convert', local_img_path, '-O', 'raw', raw_img_path])
            self.run_command(['VBoxManage', 'convertdd',raw_img_path, convert_img_path])
        else:
            convert_img_path = None
            logger.warn("Failed to export. Unknown type: %s" % (conversion_type,) )
        return convert_img_path

    def _convert_xen_to_kvm(self, image_path, download_dir):
        #!!!IMPORTANT: Change this version if there is an update to the KVM kernel
        kernel_version = "2.6.18-348.1.1.el5"

        kernel_dir = os.path.join(download_dir,"kernel")
        ramdisk_dir = os.path.join(download_dir,"ramdisk")
        mount_point = os.path.join(download_dir,"mount_point")
        for dir_path in [kernel_dir, ramdisk_dir, mount_point]:
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)
        self.run_command(["mount", "-o", "loop", image_path, mount_point])

        #PREPEND:
        for (prepend_line, prepend_to) in [ ("LABEL=root       /             ext4     defaults,errors=remount-ro 1 1", "etc/fstab")]:
            prepend_file_path = os.path.join(mount_point, prepend_to)
            if os.path.exists(prepend_file_path):
                self.run_command(["/bin/sed", "-i", "1i %s" % prepend_line, prepend_file_path])

        #REMOVE (1-line):
        for (remove_line_w_str, remove_from) in [ ("alias scsi", "etc/modprobe.conf"),
                                                  ("atmo_boot",  "etc/rc.local") ]:
            replace_file_path = os.path.join(mount_point, remove_from)
            if os.path.exists(replace_file_path):
                self.run_command(["/bin/sed", "-i", "/%s/d" % remove_line_w_str, replace_file_path])

        #REPLACE:
        for (replace_str, replace_with, replace_where) in [ ("\/dev\/sda","\#\/dev\/sda","etc/fstab"),
                                                            ("xvc0","\#xvc0","etc/inittab"),
                                                            ("xennet","8139cp","etc/modprobe.conf") ]:
            replace_file_path = os.path.join(mount_point,replace_where)
            if os.path.exists(replace_file_path):
                self.run_command(["/bin/sed", "-i", "s/%s/%s/" % (replace_str, replace_with), replace_file_path])

        #Chroot jail
        self.run_command(["/usr/sbin/chroot", mount_point, "/bin/bash", "-c", 
            "yum install kernel-%s -y; mkinitrd --with virtio_pci --with virtio_ring --with virtio_blk --with virtio_net --with virtio_balloon --with virtio -f /boot/initrd-%s.img %s" 
            % (kernel_version, kernel_version, kernel_version)])

        #Copy new kernel & ramdisk
        local_kernel_path = os.path.join(kernel_dir, "vmlinuz-%s" % kernel_version)
        local_ramdisk_path = os.path.join(ramdisk_dir, "initrd-%s.img" % kernel_version)
        mount_kernel_path = os.path.join(mount_point, "boot/vmlinuz-%s" % kernel_version)
        mount_ramdisk_path = os.path.join(mount_point, "boot/initrd-%s.img" % kernel_version)

        self.run_command(["/bin/cp", mount_kernel_path, local_kernel_path])
        self.run_command(["/bin/cp", mount_ramdisk_path, local_ramdisk_path])
        #Un-mount the image
        self.run_command(["umount", mount_point])
        return (image_path, local_kernel_path, local_ramdisk_path)

    def download_instance(self, download_dir, instance_id, local_img_path=None, remote_img_path=None):
        """
        Download an existing instance to local download directory
        Required Args:
            download_dir - The directory the image will be saved to
            instance_id - The instance ID to be downloaded (i-12341234)
        Optional Args:
            local_img_path - The path to save the image file when copied
            remote_img_path - The path to find the image file (on the node controller)
        """

        try:
            reservation = self.find_instance(instance_id)[0]
        except IndexError, no_instance:
            raise Exception("No Instance Found with ID %s" % instance_id)

        download_dir = os.path.join(download_dir,instance_id)
        for dir_path in [download_dir]:
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)

        instance = reservation.instances[0]
        owner = reservation.owner_id
        #Format empty meta strings to match current iPlant imaging standard, if not given
        if not local_img_path:
            meta_name = '%s_%s_%s_%s' % ('admin',owner, instance.id, datetime.now().strftime('%m%d%Y_%H%M%S'))
            local_img_path = '%s/%s.img' % (download_dir, meta_name )

        if not remote_img_path:
            remote_img_path = '/usr/local/eucalyptus/%s/%s/root' % (owner, instance_id)

        return self._download_remote_image(instance_id, local_img_path, remote_img_path)
        
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
        logger.debug("STDOUT: %s" % out)
        logger.debug("STDERR: %s" % err)
        return (out,err)

    def delete_image(self, image_id, bucket_name=None):
        """
        Deletes an image
        WARN: THIS IS PERMANANT! YOU HAVE BEEN WARNED!
        Required Args:
            image_id - Deregisters the image from eucalyptus
        Optional Args:
            bucket_name - If Passed, the entire image is removed from S3.
        """
        if image_id:
            euca_conn = self.euca.make_connection()
            euca_conn.deregister_image(image_id=image_id)
            logger.debug("Deleted image %s" % image_id)
            if not bucket_name:
                logger.info("NOTE: Bucket for image %s still exists." % image_id)
        if bucket_name:
            self._delete_bucket(bucket_name)
        return []


    def _delete_bucket(self, bucket_name):
        try:
            bucket = self.s3_conn.get_bucket(bucket_name)
        except S3ResponseError, all_gone:
            logger.info("The bucket %s does not exist" % bucket_name)
            return
        #Multi-object delete is best, but of course Walrus S3 fails
        #result = bucket.delete_keys([key.name for key in bucket])
        #return result.deleted
        for key in bucket:
            key.delete()
        bucket.delete()
        logger.debug("Deleted bucket %s" % bucket_name)
        return True

    def _download_remote_image(self, instance_id, local_img_path, remote_img_path):
        """
        Downloads image to local disk
        """
        #SCP remote file only if file does not exist locally
        if not os.path.exists(local_img_path):
            (nodes,instances) = self._build_instance_nc_map()
            node_controller_ip = nodes[instance_id]
            logger.info("Instance found on Node: %s" % node_controller_ip)
            return self._node_controller_scp(node_controller_ip, remote_img_path, local_img_path)

    def _upload_local_image(self, image_path, kernel, ramdisk, destination_path, parent_emi, meta_name, image_name, public, private_user_list):
        """
        Upload a local image, kernel and ramdisk to the Eucalyptus Cloud
        """
        self._bundle_image(image_path, kernel, ramdisk, destination_path, ancestor_ami_ids=[parent_emi,])
        manifest_loc = '%s/%s.img.manifest.xml' % (destination_path, meta_name )
        logger.debug(manifest_loc)
        s3_manifest_loc = self._upload_bundle(meta_name.lower(), manifest_loc)
        logger.debug(s3_manifest_loc)
        new_image_id  = self._register_bundle(s3_manifest_loc)
        logger.info("New image created! Name:%s ID:%s" % (image_name, new_image_id))
        if not public:
            euca_conn = self.euca.make_connection()
            euca_conn.modify_image_attribute(image_id = new_image_id,
                attribute = 'launchPermission',
                operation = 'remove',
                user_ids = None,
                groups = ['all'],
                product_codes = None)
            euca_conn.modify_image_attribute(image_id = new_image_id,
                attribute = 'launchPermission',
                operation = 'add',
                user_ids = private_user_list,
                groups = None,
                product_codes = None)
            
        return new_image_id

    def _old_nc_scp(self, node_controller_ip, remote_img_path, local_img_path):
        """
        Runs a straight SCP from node controller
        NOTE: no-password, SSH key access to the node controller FROM THIS MACHINE is REQUIRED
        """
        node_controller_ip = node_controller_ip.replace('172.30','128.196') 
        self.run_command(['scp', '-P1657','root@%s:%s' % (node_controller_ip, remote_img_path), local_img_path])
        return local_img_path

    def _node_controller_scp(self, node_controller_ip, remote_img_path, local_img_path, ssh_download_dir='/tmp'):
        """
        scp the RAW image from the NC to 'local_img_path'
        """
        try:
            from core.models.node import NodeController
            nc = NodeController.objects.get(alias=node_controller_ip)
        except ImportError as no_node_conf:
            return self._old_nc_scp(node_controller_ip, remote_img_path, local_img_path)
        except NodeController.DoesNotExist as node_conf_dne:
            err_msg = "Node controller %s missing - Create a new record and add it's private key to use the image manager" % node_controller_ip
            logger.error(err_msg)
            raise 

        #SCP the file if an SSH Key has been added!
        ssh_file_loc = '%s/%s' % (ssh_download_dir, 'tmp_ssh.key')
        if nc.ssh_key_added():
            ssh_key_file = open(ssh_file_loc, 'w')
            self.run_command(['echo',nc.private_ssh_key], stdout=ssh_key_file)
            ssh_key_file.close()
            self.run_command(['whoami'])
            self.run_command(['chmod','600',ssh_file_loc])
            node_controller_ip = nc.hostname
            self.run_command(['scp','-o','stricthostkeychecking=no', '-i', ssh_file_loc, '-P1657','root@%s:%s' % (node_controller_ip, remote_img_path), local_img_path])
            self.run_command(['rm','-rf',ssh_file_loc])
            return local_img_path

    """
    Indirect Create Image Functions - These functions are called indirectly during the 'create_image' process. 
    """
    def _remove_local_image(self, wildcard_path):
        """
        Expand the wildcard to match all files, delete each one.
        """
        glob_list = glob.glob(wildcard_path)
        if glob_list:
            for filename in glob_list:
                self.run_command(['/bin/rm', '-rf', filename])

    def _readd_atmo_boot(self, mount_point):
        host_atmoboot = os.path.join(settings.PROJECT_ROOT,'extras/goodies/atmo_boot')
        atmo_boot_path = os.path.join(mount_point,'usr/sbin/atmo_boot')
        self.run_command(['/bin/cp','%s' % host_atmoboot, '%s' % atmo_boot_path])

        
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


    def _bundle_image(self, image_path, kernel=None, ramdisk=None, user=None, destination_path='/tmp', target_arch='x86_64', mapping=None, product_codes=None, ancestor_ami_ids=[]):
        """
        bundle_image - Bundles an image given the correct params
        Required Params:
            image_path - Path to the image file
            kernel -  eki-###
            ramdisk - eri-###
        Optional Params:
            destination_path - (Default: /tmp) Path where the image, manifest, and parts file will reside 
            target_arch - (Default: x86_64) Targeted Architecture of the image
            user - 
            mapping  - 
            product_codes  - 
        """
        try:
            self.euca.validate_file(image_path)
        except FileValidationError, img_missing:
            print >> sys.stderr, 'Imaging process aborted. Error: Image file not found!'
            logger.error('Imaging process aborted. Error: Image file not found!')
            raise

        cert_path=self.euca.get_environ('EC2_CERT')
        private_key_path=self.euca.get_environ('EC2_PRIVATE_KEY')
        ec2cert_path=self.euca.get_environ('EUCALYPTUS_CERT')
        try:
            self.euca.validate_file(cert_path)
            self.euca.validate_file(private_key_path)
            self.euca.validate_file(ec2cert_path)
        except FileValidationError, no_file:
            print >> sys.stderr, 'Imaging process aborted. Error: Eucalyptus files not found! Did you source the admin self.eucarc?'
            logger.error('Imaging process aborted. Error: Eucalyptus files not found! Did you source the admin self.eucarc?')
            raise
        except TypeError, no_environ:
            logger.error("Image process aborted! Environment not properly set. EC2_CERT, EC2_PRIVATE_KEY, or EUCALYPTUS_CERT not found!")
            raise

        #Verify the image
        logger.debug('Verifying image')
        image_size = self.euca.check_image(image_path, destination_path)
        prefix = self.euca.get_relative_filename(image_path)
        #Tar the image file 
        logger.debug('Zipping the image')
        (tgz_file, sha_image_digest) = self.euca.tarzip_image(prefix, image_path, destination_path)
        logger.debug('Encrypting zip file')
        (encrypted_file, key, iv, bundled_size) = self.euca.encrypt_image(tgz_file)
        os.remove(tgz_file)
        #Create the encrypted File
        logger.debug('Splitting image into parts')
        parts, parts_digest = self.euca.split_image(encrypted_file)
        #Generate manifest using encrypted file
        logger.debug('Generating manifest')
        self.euca.generate_manifest(destination_path, prefix, parts, parts_digest, image_path, key, iv, cert_path, ec2cert_path, private_key_path, target_arch, image_size, bundled_size, sha_image_digest, user, kernel, ramdisk, mapping, product_codes, ancestor_ami_ids)
        logger.debug('Manifest Generated')
        #Destroyed encrypted file
        os.remove(encrypted_file)
       
    def _upload_file_to_s3(self, bucket_name, keyname, filename, canned_acl='aws-exec-read'):
        from boto.s3.connection import S3Connection as Connection
        from boto.s3.key import Key

        s3euca = Euca2ool(is_s3=True)
        s3euca.ec2_user_access_key=settings.AWS_S3_KEY
        s3euca.ec2_user_secret_key=settings.AWS_S3_SECRET
        s3euca.url = settings.AWS_S3_URL


        conn = s3euca.make_connection()
        bucket_instance = _ensure_bucket(conn, bucket_name, canned_acl)
        k = Key(bucket_instance)
        k.key = keyname
        with open(filename, "rb") as the_file:
            try:
                logger.debug("Uploading File:%s to bucket:%s // key:%s" % (filename, bucket_name, keyname))
                k.set_contents_from_file(the_file, policy=canned_acl)
                logger.debug("File Upload complete")
            except S3ResponseError, s3error:
                s3error_string = '%s' % (s3error)
                if s3error_string.find("403") >= 0:
                    logger.warn("Permission denied while writing : %s " %  k.key)
        return k
 
    def _upload_bundle(self, bucket_name, manifest_path, ec2cert_path=None, directory=None, part=None, canned_acl='aws-exec-read', skipmanifest=False):
        """
        upload_bundle - Read the manifest and upload the entire bundle (In parts) to the S3 Bucket (bucket_name)
        
        Required Args:
            bucket_name - The name of the S3 Bucket to be created
            manifest_path - The absolute path to the XML manifest
        Optional Args:
            ec2cert_path = (Default:os.environ['EC2_CERT']) The absolute path to the Admin EC2 Cert (For S3 Access)
            canned_acl - (Default:'aws-exec-read')
            skipmanifest - (Default:False) Skip manifest upload
            directory - Select directory of parts (If different than values in XML)
            part - 
        """
        from xml.dom import minidom
        from euca2ools import Euca2ool, FileValidationError, Util
        from boto.s3.connection import S3Connection as Connection
        from boto.s3.key import Key
        logger.debug("Validating the manifest")
        try:
            self.euca.validate_file(manifest_path)
        except FileValidationError, no_file:
            print 'Invalid manifest'
            logge.error("Invalid manifest file provided. Check path")
            raise

        s3euca = Euca2ool(is_s3=True)
        s3euca.ec2_user_access_key=self.euca.ec2_user_access_key
        s3euca.ec2_user_secret_key=self.euca.ec2_user_secret_key
        s3euca.url = self.s3_url

        conn = s3euca.make_connection()
        bucket_instance = _ensure_bucket(conn, bucket_name, canned_acl)
        logger.debug("S3 Bucket %s Created. Retrieving Parts from manifest" % bucket_name)
        parts = self._get_parts(manifest_path)
        if not directory:
            manifest_path_parts = manifest_path.split('/')
            directory = manifest_path.replace(manifest_path_parts[len(manifest_path_parts) - 1], '')
        if not skipmanifest and not part:
            _upload_manifest(bucket_instance, manifest_path, canned_acl)
        logger.debug("Uploading image in parts to S3 Bucket %s." % bucket_name)
        _upload_parts(bucket_instance, directory, parts, part, canned_acl)
        return "%s/%s" % (bucket_name, self.euca.get_relative_filename(manifest_path))

    def _register_bundle(self, s3_manifest_path):
        try:
            logger.debug("Registering S3 manifest file:%s with image in euca" % s3_manifest_path)
            euca_conn = self.euca.make_connection()
            image_id = euca_conn.register_image(image_location=s3_manifest_path)
            return image_id
        except Exception, ex:
            logger.error(ex)
            self.euca.display_error_and_exit('%s' % ex)

    def _build_instance_nc_map(self):
        """
        Using the 'DescribeNodes' API response, create a map with instance keys and node_controller_ip values:
            i-12341234 => 128.196.1.1 
            i-12345678 => 128.196.1.2
        """
        boto_instances = self.image_conn.get_list("DescribeNodes", {}, [('euca:item',Instance)], '/')
        last_node = ''
        nodes = {}
        instances = {}
        for inst in boto_instances:
            if hasattr(inst, 'euca:name'):
                last_node = getattr(inst, 'euca:name')
            if not hasattr(inst, 'euca:entry'):
                continue
            instance_id = getattr(inst, 'euca:entry')
            nodes[instance_id] = last_node
            if instances.get(last_node):
                instance_list = instances[last_node] 
                instance_list.append(instance_id)
            else:
                instances[last_node] = [instance_id]
        return (nodes, instances)

    """
    Indirect Download Image Functions - These functions are called indirectly during the 'download_image' process. 
    """
    def _retrieve_euca_image(self, image_location, download_dir, part_dir):
        (bucket_name,manifest_loc) = image_location.split('/')
        bucket = self.get_bucket(bucket_name)
        logger.debug("Bucket found : %s" % bucket)
        self._download_manifest(bucket, part_dir, manifest_loc)
        logger.debug("Manifest downloaded")
        part_list = self._download_parts(bucket, part_dir, manifest_loc)
        logger.debug("Image parts downloaded")
        whole_image = self._unbundle_manifest(part_dir, download_dir, os.path.join(part_dir,manifest_loc), part_list=part_list)
        return whole_image

    def _download_manifest(self, bucket, download_dir, manifest_name):
        k = Key(bucket)
        k.key = manifest_name
        man_file = open(os.path.join(download_dir, manifest_name), 'wb')
        k.get_contents_to_file(man_file)
        man_file.close()
        
    def _download_parts(self, bucket, download_dir, manifest_name):
        man_file_loc = os.path.join(download_dir, manifest_name)
        parts = self._get_parts(man_file_loc)
        logger.debug("%d parts to be downloaded" % len(parts))
        part_files = []
        for idx,part in enumerate(parts):
            part_loc = os.path.join(download_dir, part)
            part_files.append(part_loc)
            if os.path.exists(part_loc):
                #Do not re-download an existing part file
                continue
            part_file = open(part_loc, 'wb')
            k = Key(bucket)
            k.key = part
            if idx % 5 == 0:
                logger.debug("Downloading part %d/%d.." % (idx+1,len(parts)))
            k.get_contents_to_file(part_file)
            part_file.close()
        return part_files

    def _unbundle_manifest(self, source_dir, download_dir, manifest_file_loc, pk_path=settings.EUCA_PRIVATE_KEY, part_list=[]):
        private_key_path = pk_path
        #Determine # of parts in source_dir
        logger.debug("Preparing to unbundle downloaded image")
        (parts, encrypted_key, encrypted_iv) = self.euca.parse_manifest(manifest_file_loc)
        #Use euca methods to assemble parts in source_dir to create encrypted .tar
        logger.debug("Manifest parsed")
        encrypted_image = self.euca.assemble_parts(source_dir, download_dir, manifest_file_loc, parts)
        for part_loc in part_list:
            os.remove(part_loc)
        logger.debug("Encrypted image assembled")
        #Use the pk_path to unencrypt all information, using information provided from parsing the manifest to create new .tar file
        tarred_image = self.euca.decrypt_image(encrypted_image, encrypted_key, encrypted_iv, pk_path)
        os.remove(encrypted_image)
        logger.debug("Image decrypted.. Untarring")
        image = self.euca.untarzip_image(download_dir, tarred_image)
        os.remove(tarred_image)
        logger.debug("Image untarred")
        return image
    """
    Generally Indirect functions - These are useful for debugging and gathering necessary info at the REPL
    """
    def list_buckets(self):
        return self.s3_conn.get_all_buckets()

    def find_bucket(self, name):
        return [b for b in self.list_buckets() if name.lower() in b.name.lower()]

    def get_bucket(self, bucket_name):
        return self.s3_conn.get_bucket(bucket_name)

    def list_instances(self):
        euca_conn = self.euca.make_connection()
        return euca_conn.get_all_instances()

    def find_instance(self, name):
        return [m for m in self.list_instances() if name.lower() in m.instances[0].id.lower()]

    def list_images(self):
        euca_conn = self.euca.make_connection()
        return euca_conn.get_all_images()

    def find_image(self, name):
        return [m for m in self.list_images() if name.lower() in m.location.lower()]

    def get_image(self, image_id):
        euca_conn = self.euca.make_connection()
        return euca_conn.get_image(image_id)


    #Parsing classes belong to euca-download-bundle in euca2ools 1.3.1
    def _get_parts(self, manifest_filename):
        parts = []
        dom = minidom.parse(manifest_filename)
        manifest_elem = dom.getElementsByTagName('manifest')[0]
        parts_list = manifest_elem.getElementsByTagName('filename')
        for part_elem in parts_list:
            nodes = part_elem.childNodes
            for node in nodes:
                if node.nodeType == node.TEXT_NODE:
                    parts.append(node.data)
        return parts


"""
These functions belong to euca-upload-bundle in euca2ools 1.3.1
"""
def _create_bucket(connection, bucket, canned_acl=None):
    print 'Creating bucket:', bucket
    return connection.create_bucket(bucket, policy=canned_acl)

def _ensure_bucket(connection, bucket, canned_acl=None):
    bucket_instance = None
    try:
        print 'Checking bucket:', bucket
        bucket_instance = connection.get_bucket(bucket)
    except S3ResponseError, s3error:
        s3error_string = '%s' % (s3error)
        if (s3error_string.find("404") >= 0):
            try:
                bucket_instance = _create_bucket(connection, bucket, canned_acl)
            except S3CreateError:
                print 'Unable to create bucket %s' % (bucket)
                sys.exit()
        elif (s3error_string.find("403") >= 0):
            print "You do not have permission to access bucket:", bucket
            sys.exit()
        else:
            print s3error_string
            sys.exit()
    return bucket_instance


def _get_relative_filename(filename):
    f_parts = filename.split('/')
    return f_parts[len(f_parts) - 1]

def _upload_manifest(bucket_instance, manifest_filename, canned_acl=None):
    print 'Uploading manifest file'
    k = Key(bucket_instance)
    k.key = _get_relative_filename(manifest_filename)
    manifest_file = open(manifest_filename, "rb")
    try:
        k.set_contents_from_file(manifest_file, policy=canned_acl)
    except S3ResponseError, s3error:
        s3error_string = '%s' % (s3error)
        if (s3error_string.find("403") >= 0):
            print "Permission denied while writing:", k.key
        else:
            print s3error_string
        sys.exit()

def _upload_parts(bucket_instance, directory, parts, part_to_start_from, canned_acl=None):
    if part_to_start_from:
        okay_to_upload = False
    else:
        okay_to_upload = True

    for part in parts:
        if part == part_to_start_from:
            okay_to_upload = True
        if okay_to_upload:
            print 'Uploading part:', part
            k = Key(bucket_instance)
            k.key = part
            part_file = open(os.path.join(directory, part), "rb")
            try:
                k.set_contents_from_file(part_file, policy=canned_acl)
            except S3ResponseError, s3error:
                s3error_string = '%s' % (s3error)
                if (s3error_string.find("403") >= 0):
                    print "Permission denied while writing:", k.key
                else:
                    print s3error_string
                sys.exit()

