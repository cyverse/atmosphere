"""
MigrationManager:
    Use this class to describe processes to move images from one cloud to another

Migrating an Instance/Image (Example: Eucalyptus --> Openstack)
>> manager.migrate_image('/temp/image/path/', 'emi-F1F122E4')
    _OR_
>> manager.migrate_instance('/temp/image/path/', 'i-12345678')

>> os_manager.upload_euca_image('Migrate emi-F1F122E4', 
                                '/temp/image/path/name_of.img', 
                                '/temp/image/path/kernel/vmlinuz-...el5', 
                                '/temp/image/path/ramdisk/initrd-...el5.img')
"""
from atmosphere.logger import logger
from service.drivers.openstackImageManager import ImageManager as OSImageManager
from service.drivers.eucalyptusImageManager import ImageManager as EucaImageManager
import os
import glob
class EucaToOpenstack:

    def __init__(self):
        self.os_img_manager = OSImageManager()
        self.euca_img_manager = EucaImageManager()

    def migrate_image(self, euca_image_id, name, download_path='/tmp/', euca_image_path=None, no_upload=False, keep_image=False):
        """
        Download/clean euca image
        Perform conversion
        Upload image to glance
        TODO: Add in public, private_user_list, exclude_files
        """
        if not euca_image_path:
            euca_image_path = self.euca_img_manager.download_image(download_path, euca_image_id)
            #Downloads image to download_path/emi-###
            download_path = os.path.join(download_path, euca_image_id)
            mount_point = os.path.join(download_path,'mount_point')
            self.euca_img_manager._clean_local_image(euca_image_path, mount_point, ["usr/sbin/atmo_boot"])
        distro = self._determine_distro(euca_image_path, download_path)
        if distro == 'centos':
            (image, kernel, ramdisk) = self._convert_centos(euca_image_path, download_path)
        elif distro == 'ubuntu':
            (image, kernel, ramdisk) = self._convert_ubuntu(euca_image_path, download_path, euca_image_id)
        else:
            logger.error("Failed to find a conversion for this OS.")
            return

        if not no_upload:
            os_image = self.os_img_manager.upload_euca_image(name, image, kernel, ramdisk)
        if not keep_image:
            os.remove(image)
            os.remove(kernel)
            os.remove(ramdisk)
        if os_image:
            return os_image

    def migrate_instance(self, euca_instance_id, name, download_path='/tmp/', euca_image_path=None, no_upload=False, keep_image=False):
        """
        TODO: Add in public, private_user_list, exclude_files
        """
        if not euca_image_path:
            euca_image_path = self.euca_img_manager.download_instance(download_path, euca_instance_id)
            #Downloads instance to download_path/i-###
            download_path = os.path.join(download_path, euca_instance_id)
            mount_point = os.path.join(download_path, 'mount_point')
            self.euca_img_manager._clean_local_image(euca_image_path, mount_point, ["usr/sbin/atmo_boot"])
        distro = self._determine_distro(euca_image_path, download_path)
        logger.info("Migrating using the %s distro conversion" % distro)
        if distro == 'centos':
            (image, kernel, ramdisk) = self._convert_centos(euca_image_path, download_path)
        elif distro == 'ubuntu':
            euca_image_id = self.euca_img_manager.find_instance('i-3F57078F')[0].instances[0].image_id
            (image, kernel, ramdisk) = self._convert_ubuntu(euca_image_path, download_path, euca_image_id)
        else:
            logger.error("Failed to find a conversion for this OS.")
            return
        if not no_upload:
            os_instance = self.os_img_manager.upload_euca_image(name, image, kernel, ramdisk)
        if not keep_image:
            os.remove(image)
            os.remove(kernel)
            os.remove(ramdisk)
        if os_instance:
            return os_instance

    def _determine_distro(self, image_path, download_dir):
        """
        """
        mount_point = os.path.join(download_dir,"mount_point")

        for dir_path in [mount_point]:
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)

        self.euca_img_manager.run_command(["mount", "-o", "loop", image_path, mount_point])

        issue_file = os.path.join(mount_point, "etc/issue.net")
        (issue_out,err) = self.euca_img_manager.run_command(["cat", issue_file])

        #release_file = os.path.join(mount_point, "etc/*release*")
        #(centos_out,err) = self.euca_img_manager.run_command(['/usr/bin/env', 'bash', '-c', 'cat %s' % release_file])

        self.euca_img_manager.run_command(["umount", mount_point])

        if 'ubuntu' in issue_out.lower():
            return 'ubuntu'
        elif 'centos' in issue_out.lower():
            return 'centos'
        else:
            return 'unknown'
        
    def _convert_ubuntu(self, image_path, download_dir, euca_image_id):
        """
        Clean the image as you would normally, but apply a few specific changes
        Returns: ("/path/to/img", "/path/to/kernel", "/path/to/ramdisk")
        """
        #!!!IMPORTANT: Change this version if there is an update to the KVM kernel

        kernel_dir = os.path.join(download_dir,"kernel")
        ramdisk_dir = os.path.join(download_dir,"ramdisk")
        mount_point = os.path.join(download_dir,"mount_point")

        for dir_path in [kernel_dir, ramdisk_dir, mount_point]:
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)

        #Mount the image
        self.euca_img_manager.run_command(["mount", "-o", "loop", image_path, mount_point])
        #REMOVE (1-line):
        for (remove_line_w_str, remove_from) in [ ("atmo_boot",  "etc/rc.local"),
                                                  ("sda2", "etc/fstab"),
                                                  ("sda3",  "etc/fstab") ]:
            replace_file_path = os.path.join(mount_point, remove_from)
            if os.path.exists(replace_file_path):
                self.euca_img_manager.run_command(["/bin/sed", "-i", "/%s/d" % remove_line_w_str, replace_file_path])

        #Un-mount the image
        self.euca_img_manager.run_command(["umount", mount_point])

        image = self.euca_img_manager.get_image(euca_image_id)
        kernel = self.euca_img_manager.get_image(image.kernel_id)
        ramdisk = self.euca_img_manager.get_image(image.ramdisk_id)

        kernel_fname  = self.euca_img_manager._retrieve_euca_image(kernel.location, kernel_dir, kernel_dir)[0]
        ramdisk_fname = self.euca_img_manager._retrieve_euca_image(ramdisk.location, ramdisk_dir, ramdisk_dir)[0]

        kernel_path = os.path.join(kernel_dir,kernel_fname)
        ramdisk_path = os.path.join(ramdisk_dir,ramdisk_fname)

        return (image_path, kernel_path, ramdisk_path)

    def _convert_centos(self, image_path, download_dir):
        """
        Clean the image as you would normally, but apply a few specific changes
        Returns: ("/path/to/img", "/path/to/kernel", "/path/to/ramdisk")
        """
        (image, kernel, ramdisk) = self.euca_img_manager._openstack_kvm_export(image_path, download_dir)
        new_image = self.euca_img_manager._build_new_image(image, download_dir)
        return (new_image, kernel, ramdisk)
