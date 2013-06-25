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
import os
import glob
import shutil

from threepio import logger

from service.drivers.openstackImageManager import ImageManager as OSImageManager
from service.drivers.eucalyptusImageManager import ImageManager as EucaImageManager
from service.system_calls import run_command
from service.imaging.common import mount_image
from service.imaging.convert import xen_to_kvm_ubuntu

class EucaOSMigrater:

    def __init__(self, euca_creds, os_creds):
        self.os_img_manager = OSImageManager(**os_creds)
        self.euca_img_manager = EucaImageManager(**euca_creds)

    def migrate_image(self, euca_image_id, name, local_download_dir='/tmp/', euca_image_path=None, no_upload=False, keep_image=False):
        """
        Download/clean euca image
        Perform conversion
        Upload image to glance
        TODO: Add in public, private_user_list, exclude_files
        """
        if not euca_image_path:
            local_download_dir, euca_image_path = self._download_and_clean_image(local_download_dir, euca_image_id)
        distro = self._determine_distro(euca_image_path, local_download_dir)
        if distro == 'centos':
            (image, kernel, ramdisk) = self._euca_rhel_migration(euca_image_path, local_download_dir)
        elif distro == 'ubuntu':
            (image, kernel, ramdisk) = self._euca_debian_migration(euca_image_path, local_download_dir, euca_image_id)
        else:
            logger.error("Failed to find a conversion for this OS.")
            return
        logger.debug("Image ready for upload")
        if not no_upload:
            os_image = self.os_img_manager.upload_euca_image(name, image, kernel, ramdisk)
        if not keep_image:
            os.remove(image)
            os.remove(kernel)
            os.remove(ramdisk)
        if os_image:
            return os_image

    def migrate_instance(self, euca_instance_id, name, local_download_dir='/tmp/', meta_name=None, euca_image_path=None, no_upload=False, keep_image=False):
        """
        TODO: Add in public, private_user_list, exclude_files
        """
        if not euca_image_path:
            local_download_dir, euca_image_path = self.euca_img_manager.download_instance(local_download_dir,
                    euca_instance_id, meta_name=meta_name)
            #Downloads instance to local_download_dir/user/i-###
            mount_point = os.path.join(local_download_dir, 'mount_point')
            self.euca_img_manager._clean_local_image(euca_image_path, mount_point, ["usr/sbin/atmo_boot"])
        distro = self._determine_distro(euca_image_path, local_download_dir)
        logger.info("Migrating using the %s distro conversion" % distro)
        if distro == 'centos':
            (image, kernel, ramdisk) = self._euca_rhel_migration(euca_image_path, local_download_dir)
        elif distro == 'ubuntu':
            euca_image_id = self.euca_img_manager.find_instance(euca_instance_id)[0].instances[0].image_id
            (image, kernel, ramdisk) = self._euca_debian_migration(euca_image_path, local_download_dir, euca_image_id)
        else:
            logger.error("Failed to find a conversion for this OS.")
            return
        if not no_upload:
            os_image = self.os_img_manager.upload_euca_image(name, image, kernel, ramdisk)
            logger.debug("Successfully uploaded eucalyptus image: %s" %
                    os_image)
        #if not keep_image:
        #    shutil.rmtree(local_download_dir)
        if os_image:
            return os_image.id

    def _download_and_clean_image(self, local_download_dir, euca_image_id):
        local_download_dir, euca_image_path = self.euca_img_manager.download_image(local_download_dir, euca_image_id)
        mount_point = os.path.join(local_download_dir, 'mount_point')
        self.euca_img_manager._clean_local_image(euca_image_path, mount_point, ["usr/sbin/atmo_boot"])
        return local_download_dir, euca_image_path

    def _determine_distro(self, image_path, download_dir):
        """
        """
        mount_point = os.path.join(download_dir,"mount_point")

        for dir_path in [mount_point]:
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)

        out, err = mount_image(image_path, mount_point)
        if err:
            raise Exception("Encountered errors mounting image:%s" % err)

        issue_file = os.path.join(mount_point, "etc/issue.net")
        (issue_out,err) = run_command(["cat", issue_file])

        run_command(["umount", mount_point])

        if 'ubuntu' in issue_out.lower():
            return 'ubuntu'
        elif 'centos' in issue_out.lower():
            return 'centos'
        else:
            return 'unknown'
        
    def _euca_debian_migration(self, image_path, download_dir, euca_image_id):
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
        mount_image(image_path, mount_point)

        xen_to_kvm_ubuntu(mount_point)

        #Un-mount the image
        run_command(["umount", mount_point])

        image = self.euca_img_manager.get_image(euca_image_id)
        kernel = self.euca_img_manager.get_image(image.kernel_id)
        ramdisk = self.euca_img_manager.get_image(image.ramdisk_id)

        kernel_fname  = self.euca_img_manager._unbundle_euca_image(
            kernel.location, kernel_dir, 
            kernel_dir, self.euca_img_manager.pk_path)[0]
        ramdisk_fname = self.euca_img_manager._unbundle_euca_image(
            ramdisk.location, ramdisk_dir,
            ramdisk_dir, self.euca_img_manager.pk_path)[0]

        kernel_path = os.path.join(kernel_dir,kernel_fname)
        ramdisk_path = os.path.join(ramdisk_dir,ramdisk_fname)

        return (image_path, kernel_path, ramdisk_path)

    def _euca_rhel_migration(self, image_path, download_dir):
        """
        Clean the image as you would normally, but apply a few specific changes
        Returns: ("/path/to/img", "/path/to/kernel", "/path/to/ramdisk")
        """
        (image, kernel, ramdisk) = self.euca_img_manager._prepare_kvm_export(image_path, download_dir)
        return (image, kernel, ramdisk)
