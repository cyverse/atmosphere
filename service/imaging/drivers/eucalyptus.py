"""
ImageManager:
    Remote Eucalyptus Image management (euca2ools 1.3.1 + boto ec2)

Creating an Image from an Instance (Manual image requests)

>> from service.imaging.drivers.eucalyptus import ImageManager
>> manager = ImageManager()
>> manager.create_image('i-12345678', 'New image name v1')

>> os_manager.upload_euca_image('Migrate emi-F1F122E4',
                                '/temp/image/path/name_of.img',
                                '/temp/image/path/kernel/vmlinuz-...el5',
                                '/temp/image/path/ramdisk/initrd-...el5.img')
"""

import time
import sys
import os
import math
import subprocess

from datetime import datetime
from urlparse import urlparse
from xml.dom import minidom

from boto import connect_ec2
from boto.ec2.regioninfo import RegionInfo
from boto.ec2.instance import Instance as BotoInstance
from boto.s3.connection import S3Connection, OrdinaryCallingFormat
from boto.exception import S3ResponseError, S3CreateError, EC2ResponseError
from boto.s3.key import Key

from euca2ools import Euca2ool, FileValidationError

from service.imaging.common import sed_delete_multi, sed_delete_one
from service.imaging.common import sed_replace, sed_prepend

from service.imaging.common import run_command, wildcard_remove
from service.imaging.common import mount_image, remove_files, get_latest_ramdisk
from service.imaging.clean import remove_user_data, remove_atmo_data,\
                                  remove_vm_specific_data
from service.imaging.convert import xen_to_kvm_centos

from threepio import logger


class ImageManager():
    """
    Convienence class that uses a combination of boto and euca2ools calls
    to remotely download an image form the cloud
    """
    s3_conn = None
    euca = None
    s3_url = None

    def __init__(self, *args, **kwargs):
        """
        All credentials are necessary to Private Key file required to decrypt images.
        """
        #Collect credentials
        #kwargs, fallback to environment args
        (key, secret, ec2_url, s3_url) = self._get_credentials(**kwargs)
        self._imaging_credentials(**kwargs)
        (key, secret, ec2_url, s3_url) = self._env_credentials(key, secret, ec2_url, s3_url)
        self.s3_url = s3_url

        #Initialize connections
        self.euca = self._init_euca2ool(key, secret, ec2_url)
        self.s3_conn = self._boto_s3_conn(key, secret, s3_url)
        self.image_conn = self._boto_ec2_conn(key, secret, ec2_url)

    def create_image(self, instance_id, image_name, public=True,
                     private_user_list=[], exclude=[], kernel=None,
                     ramdisk=None, meta_name=None,
                     local_download_dir='/tmp', local_image_path=None,
                     clean_image=True, remote_img_path=None, keep_image=False):
        """
        Creates an image of a running instance
        Required Args:
            instance_id - The instance that will be imaged
            image_name - The name of the image
        Optional Args (That are required for euca):
            public - Should image be accessible for other users?
            (Default: True)
            private_user_list  - List of users who should get access
            (Default: [])
            kernel  - Associated Kernel for image
            (Default is instance.kernel)
            ramdisk - Associated Ramdisk for image
            (Default is instance.ramdisk)
        Optional Args:
            meta_name - Override the default naming convention
            local_download_dir - Override the default download dir
            (All files will be temporarilly stored here, then deleted
            remote_img_path - Override the default path to the image
            (On the Node Controller -- Must be exact to the image file (root))
        """

        try:
            reservation, instance = self.find_instance(instance_id)
            #Collect information about instance to fill arguments
            owner = reservation.owner_id
            instance_kernel = reservation.instances[0].kernel
            instance_ramdisk = reservation.instances[0].ramdisk
            parent_emi = reservation.instances[0].image_id
        except IndexError:
            raise Exception("No Instance Found with ID %s" % instance_id)

        logger.info("Instance %s belongs to: %s" % (instance_id, owner))
        #Prepare private list, if necessary
        if not public and owner not in private_user_list:
            private_user_list.append(owner)
        # Collect kernel, ramdisk
        if not kernel:
            kernel = instance_kernel
        if not ramdisk:
            ramdisk = instance_ramdisk

        #Format paths for downloading
        if not remote_img_path:
            remote_img_path = self._format_nc_path(owner, instance_id)
        if not meta_name:
            #meta strings should match current iPlant
            #image naming convention
            meta_name = self._format_meta_name(image_name, owner, creator='admin')

        #Image doesn't exist locally, download it
        if not local_image_path:
            local_download_dir = os.path.join(local_download_dir, owner, instance_id)
            if not os.path.exists(local_download_dir):
                os.makedirs(local_download_dir)
            local_image_path = os.path.join(local_download_dir, '%s.img' % meta_name)

            ##Run sub-scripts to retrieve,
            node_controller_ip = self._find_node(instance_id)
            self._retrieve_instance(node_controller_ip,
                                        local_image_path, remote_img_path)

        #ASSERT: by this line -- local_image_path contains a complete RAW img
        # mount and clean image 
        if clean_image:
            self._clean_local_image(
                local_image_path, 
                os.path.join(local_download_dir, 'mount/'),
                exclude=exclude)

        #upload image
        new_image_id = self._upload_instance(
            local_image_path, kernel, ramdisk, local_download_dir, parent_emi,
            meta_name, image_name, public, private_user_list)

        #Cleanup, return
        if not keep_image:
            wildcard_remove(os.path.join(local_download_dir, '%s*' % meta_name))

        return new_image_id

    def download_instance(self, download_dir, instance_id,
                          local_img_path=None, remote_img_path=None,
                          meta_name=None):
        """
        Download an existing instance to local download directory
        Required Args:
            download_dir - The directory the image will be saved to
            instance_id - The instance ID to be downloaded (i-12341234)
        Optional Args:
            local_img_path - The path to save the image file when copied
            remote_img_path - The path to find the image file
            (on the node controller)
        """

        try:
            reservation, instance = self.find_instance(instance_id)
            owner = reservation.owner_id
        except IndexError:
            raise Exception("No Instance Found with ID %s" % instance_id)

        download_dir = os.path.join(download_dir, owner, instance_id)
        for dir_path in [download_dir]:
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)

        if not meta_name:
            meta_name = self._format_meta_name(instance.id, owner)

        if not local_img_path:
            #Format empty meta strings to match
            #current iPlant imaging standard, if not given
            local_img_path = '%s/%s.img' % (download_dir, meta_name)

        if not remote_img_path:
            remote_img_path = self._format_nc_path(owner, instance_id)

        node_controller_ip = self._find_node(instance_id)
        return download_dir, self._retrieve_instance(node_controller_ip,
                                                     local_img_path,
                                                     remote_img_path)

    def download_image(self, download_dir, image_id):
        """
        Download an existing image to local download directory
        Required Args:
            download_dir - The directory the image will be saved to
            (/path/to/dir/)
            image_id - The image ID to be downloaded
            (eki-12341234, emi-12345678, eri-11111111)
        """
        machine = self.get_image(image_id)
        if not machine:
            raise Exception("Machine Not Found.")

        #We need more directories to store things..
        download_dir, part_dir = self._download_image_dirs(download_dir, image_id)

        #Get image location and unbundle the files based on the manifest and
        #parts
        image_location = machine.location
        whole_image = self._unbundle_euca_image(image_location, download_dir,
                                                part_dir, self.pk_path)[0]
        #Return download_path and image_path
        return download_dir, os.path.join(download_dir, whole_image)

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
                logger.info("NOTE: Bucket for image %s still exists."
                            % image_id)
        if bucket_name:
            self._delete_bucket(bucket_name)
        return []

    def _prepare_kvm_export(self, image_path, download_dir):
        """
        Prepare a KVM export (For OpenStack)
        Will also remove Euca-Specific files and add OS-Specific files
        """
        (kernel_dir, ramdisk_dir, mount_point) = self._export_dirs(download_dir)

        #Labeling the image as 'root' allows for less reliance on UUID
        run_command(['e2label', image_path, 'root'])

        out, err = mount_image(image_path, mount_point)
        if err:
            raise Exception("Encountered errors mounting the image: %s" % err)

        xen_to_kvm_centos(mount_point)

        #Determine the latest (KVM) ramdisk to use
        latest_rmdisk, rmdisk_version = get_latest_ramdisk(mount_point)

        #Copy new kernel & ramdisk to the folder
        local_ramdisk_path = self._copy_ramdisk(mount_point, rmdisk_version, ramdisk_dir)
        local_kernel_path = self._copy_kernel(mount_point, rmdisk_version, kernel_dir)

        run_command(["umount", mount_point])

        #Your new image is ready for upload to OpenStack 
        return (image_path, local_kernel_path, local_ramdisk_path)

    # __init__ privates
    def _get_credentials(self, **kwargs):
        key=kwargs.get('key','')
        secret=kwargs.get('secret','')
        ec2_url=kwargs.get('ec2_url','')
        s3_url=kwargs.get('s3_url','')
        return (key, secret, ec2_url, s3_url)

    def _imaging_credentials(self, **kwargs):
        self.ec2_cert_path=kwargs.get('ec2_cert_path','')
        self.pk_path=kwargs.get('pk_path','')
        self.euca_cert_path=kwargs.get('euca_cert_path','')
        self.extras_root=kwargs.get('extras_root')
        self.config_path=kwargs.get('config_path','/services/Configuration')

    def _env_credentials(self, key, secret, ec2_url, s3_url):
        #Environment fall-back
        if not key:
            key = os.environ['EC2_ACCESS_KEY']
        if not secret:
            secret = os.environ['EC2_SECRET_KEY']
        if not ec2_url:
            ec2_url = os.environ['EC2_URL']
        if not s3_url:
            s3_url = os.environ['S3_URL']
        if not self.ec2_cert_path:
            self.ec2_cert_path = os.environ['EC2_CERT']
        if not self.pk_path:
            self.pk_path = os.environ['EC2_PRIVATE_KEY']
        if not self.euca_cert_path:
            self.euca_cert_path = os.environ['EUCALYPTUS_CERT']
        return (key, secret, ec2_url, s3_url)

    def _init_euca2ool(self, key, secret, url, is_s3=False):
        # Argv must be reset to stop euca from gobbling bad sys.argv's
        sys.argv = []
        euca = Euca2ool(
            short_opts=None,
            long_opts=None,
            is_s3=is_s3,
            compat=False)

        #Prepare euca environment
        euca.ec2_user_access_key = key
        euca.ec2_user_secret_key = secret
        euca.url = url
        euca.environ['EC2_CERT'] = self.ec2_cert_path
        euca.environ['EUCALYPTUS_CERT'] = self.euca_cert_path
        euca.environ['EC2_PRIVATE_KEY'] = self.pk_path
        return euca

    def _boto_s3_conn(self, key, secret, s3_url):
        parsed_url = urlparse(s3_url)
        s3_conn = S3Connection(
            aws_access_key_id=key,
            aws_secret_access_key=secret,
            is_secure=('https' in parsed_url.scheme),
            host=parsed_url.hostname, port=parsed_url.port,
            path=parsed_url.path,
            calling_format=OrdinaryCallingFormat())
        return s3_conn

    def _boto_ec2_conn(self, key, secret, ec2_url, region='eucalyptus',
            version='eucalyptus', config_path='/services/Configuration'):
        parsed_url = urlparse(ec2_url)
        region = RegionInfo(None, region, parsed_url.hostname)
        image_conn = connect_ec2(
            aws_access_key_id=key,
            aws_secret_access_key=secret,
            is_secure=False, region=region,
            port=parsed_url.port, path=config_path)
        image_conn.APIVersion = version
        return image_conn

    # Download privates
    def _download_image_dirs(self, download_dir, image_id):
        download_dir = os.path.join(download_dir, image_id)
        part_dir = os.path.join(download_dir, 'parts')

        for dir_path in [part_dir]:
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)
        return download_dir, part_dir

    # KVM/Openstack privates
    def _export_dirs(self, download_dir):
        kernel_dir = os.path.join(download_dir, "kernel")
        ramdisk_dir = os.path.join(download_dir, "ramdisk")
        mount_point = os.path.join(download_dir, "mount_point")
        for dir_path in [kernel_dir, ramdisk_dir, mount_point]:
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)
        return (kernel_dir, ramdisk_dir, mount_point)

    def _copy_kernel(self, mount_point, rmdisk_version, kernel_dir):
        local_kernel_path = os.path.join(kernel_dir,
                                         "vmlinuz-%s" % rmdisk_version)
        mount_kernel_path = os.path.join(mount_point,
                                         "boot/vmlinuz-%s" % rmdisk_version)
        run_command(["/bin/cp", mount_kernel_path, local_kernel_path])
        return local_kernel_path

    def _copy_ramdisk(self, mount_point, rmdisk_version, ramdisk_dir):
        local_ramdisk_path = os.path.join(ramdisk_dir,
                                          "initrd-%s.img" % rmdisk_version)
        mount_ramdisk_path = os.path.join(mount_point,
                                          "boot/initrd-%s.img"
                                          % rmdisk_version)
        run_command(["/bin/cp", mount_ramdisk_path, local_ramdisk_path])
        return local_ramdisk_path

    def _get_latest_ramdisk(self, mount_point):
        (output,stder) = run_command(["/usr/sbin/chroot", mount_point, "/bin/bash", "-c", "ls -Fah /boot/"])
        latest_rmdisk = ''
        rmdisk_version = ''
        for line in output.split('\n'):
            if 'initrd' in line and 'xen' not in line:
                latest_rmdisk = line
                rmdisk_version = line.replace('.img','').replace('initrd-','')
        return latest_rmdisk, rmdisk_version


    def _get_stage_files(self, root_dir, distro):
        if distro == 'centos':
            run_command(['/bin/bash','-c','cp -f %s/extras/export/grub_files/centos/* %s/boot/grub/' % (self.extras_root, root_dir)])
        elif distro == 'ubuntu':
            run_command(['/bin/bash','-c','cp -f %s/extras/export/grub_files/ubuntu/* %s/boot/grub/' % (self.extras_root, root_dir)])

    def _format_meta_name(self, name, owner, timestamp_str=None, creator='admin'):

        if not timestamp_str:
            timestamp_str = datetime.now().strftime('%m%d%Y_%H%M%S')
        #Prepare name for imaging
        name = name.replace(' ', '_').replace('/', '-')
        meta_name = '%s_%s_%s_%s' % (creator, owner, name, timestamp_str)
        return meta_name

    def _format_nc_path(self, owner, instance_id,
            prefix='/usr/local/eucalyptus', disk='root'):
        return os.path.join(prefix, owner, instance_id, disk)

    def _find_node(self, instance_id):
        (nodes, instances) = self._build_instance_nc_map()
        node_controller_ip = nodes[instance_id]
        logger.info("Instance found on Node: %s" % node_controller_ip)
        return node_controller_ip

    #Delete privates
    def _delete_bucket(self, bucket_name):
        try:
            bucket = self.s3_conn.get_bucket(bucket_name)
        except S3ResponseError:
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

    def _retrieve_instance(self, node_controller_ip,
                        local_img_path, remote_img_path):
        """
        Downloads image to local disk
        """
        #SCP remote file only if file does not exist locally
        if not os.path.exists(local_img_path):
            return self._node_controller_scp(node_controller_ip,
                                             remote_img_path,
                                             local_img_path)
        return local_img_path

        
    def _upload_instance(self, image_path, kernel, ramdisk,
                            destination_path, parent_emi, bucket_name,
                            image_name, public, private_user_list):
        """
        Upload a local image, kernel and ramdisk to the Eucalyptus Cloud
        """
        ancestor_ami_ids = [parent_emi, ] if parent_emi else []

        new_image_id = self._upload_and_register(
                image_path, bucket_name, kernel, ramdisk,
                destination_path, ancestor_ami_ids)

        if not public:
            try:
                #Someday this will matter. Euca doesn't respect it though..
                euca_conn = self.euca.make_connection()
                euca_conn.modify_image_attribute(
                    image_id=new_image_id,
                    attribute='launchPermission',
                    operation='remove',
                    groups=['all'],
                    product_codes=None)
                euca_conn.modify_image_attribute(
                    image_id=new_image_id,
                    attribute='launchPermission',
                    operation='add',
                    user_ids=private_user_list)
            except EC2ResponseError, call_failed:
                #Since Euca ignores this anyway, lets just continue.
                logger.error("Private List - %s" % private_user_list)
                logger.exception(call_failed)
        return new_image_id

    def _upload_new_image(self, new_image_name, image_path, 
                          kernel_path, ramdisk_path, bucket_name,
                          download_dir='/tmp', private_users=[], uploaded_by='admin'):
        public = False
        if not private_users:
            public = True

        kernel_id = self._upload_kernel(kernel_path, bucket_name, download_dir)
        ramdisk_id = self._upload_ramdisk(ramdisk_path, bucket_name, download_dir)

        new_image_path = os.path.join(
                            os.path.dirname(image_path),
                            '%s%s' % (self._format_meta_name(new_image_name,uploaded_by),
                                      os.path.splitext(image_path)[1]))
        #In order to use the image name we must change the name during upload
        # to match the 'metadata' criteria for an image on atmosphere
        os.rename(image_path,new_image_path)
        new_image_id = self._upload_instance(new_image_path, kernel_id, ramdisk_id,
                                             download_dir, None, bucket_name,
                                             new_image_name, public,
                                             private_users) 
        os.rename(new_image_path,image_path)

        return (kernel_id, ramdisk_id, new_image_id)

    def _upload_kernel(self, image_path, bucket_name, download_dir='/tmp'):
        return self._upload_and_register(image_path, bucket_name,
                kernel='true', download_dir=download_dir)

    def _upload_ramdisk(self, image_path, bucket_name, download_dir='/tmp'):
        return self._upload_and_register(image_path, bucket_name,
                ramdisk='true', download_dir=download_dir)

    def _upload_and_register(self, image_path, bucket_name, kernel=None, ramdisk=None,
                            download_dir='/tmp', ancestor_ami_ids=None):
        bucket_name = bucket_name.lower()
        logger.debug('Bundling image %s to dir:%s'
                     % (image_path, download_dir))
        manifest_loc = self._bundle_image(image_path, download_dir, 
                                          kernel, ramdisk,
                                          ancestor_ami_ids=ancestor_ami_ids)
        logger.debug(manifest_loc)
        s3_manifest = self._upload_bundle(bucket_name, manifest_loc)
        new_image_id = self._register_bundle(s3_manifest)
        logger.info("New image created! ID:%s"
                    % new_image_id)
        return new_image_id


    def _old_nc_scp(self, node_controller_ip, remote_img_path, local_img_path):
        """
        Runs a straight SCP from node controller
        NOTE: no-password, SSH key access to the node controller
        FROM THIS MACHINE is REQUIRED
        """
        node_controller_ip = node_controller_ip.replace('172.30', '128.196')
        run_command(['scp', '-P1657',
                          'root@%s:%s' % (node_controller_ip, remote_img_path),
                          local_img_path])
        return local_img_path

    def _node_controller_scp(self, node_controller_ip, remote_img_path,
                             local_img_path, ssh_download_dir='/tmp'):
        """
        scp the RAW image from the NC to 'local_img_path'
        """
        try:
            from core.models.node import NodeController
            nc = NodeController.objects.get(alias=node_controller_ip)
        except ImportError:
            logger.exception("Unable to import or use node controller.")
            return self._old_nc_scp(node_controller_ip,
                                    remote_img_path, local_img_path)
        except NodeController.DoesNotExist:
            err_msg = "Node controller %s missing - Create a new record "
            err_msg += "and add it's private key to use the image manager"
            err_msg %= (node_controller_ip,)
            logger.error(err_msg)
            raise

        #SCP the file if an SSH Key has been added!
        ssh_file_loc = '%s/%s' % (ssh_download_dir, 'tmp_ssh.key')
        if nc.ssh_key_added():
            ssh_key_file = open(ssh_file_loc, 'w')
            run_command(['echo', nc.private_ssh_key], stdout=ssh_key_file)
            ssh_key_file.close()
            run_command(['whoami'])
            run_command(['chmod', '600', ssh_file_loc])
            node_controller_ip = nc.hostname
            scp_command_list = ['scp', '-o', 'stricthostkeychecking=no', '-i',
                              ssh_file_loc, '-P1657',
                              'root@%s:%s'
                              % (node_controller_ip, remote_img_path),
                              local_img_path]
            logger.info(' '.join(map(str,scp_command_list)))
            run_command(scp_command_list)
            run_command(['rm', '-rf', ssh_file_loc])
            return local_img_path

    """
    Indirect Create Image Functions -
    These functions are called indirectly during the 'create_image' process.
    """
    def _readd_atmo_boot(self, mount_point):
        #TODO: This function should no longer be necessary.
        #If it is, we need to recreate goodies/atmo_boot
        host_atmoboot = os.path.join(self.extras_root,
                                     'extras/goodies/atmo_boot')
        atmo_boot_path = os.path.join(mount_point, 'usr/sbin/atmo_boot')
        run_command(['/bin/cp', '%s' % host_atmoboot,
                          '%s' % atmo_boot_path])

    def _check_mount_path(self, filepath):
        if not filepath:
            return filepath
        if filepath.startswith('/'):
            logger.warn("WARNING: File %s has a LEADING slash. "
                        + "This causes the changes to occur on "
                        + "the HOST MACHINE and must be changed!"
                        % rm_file)
            filepath = filepath[1:]
        return filepath

    def _clean_local_image(self, image_path, mount_point, exclude=[]):
        """
        NOTE: When adding to this list,
        NEVER ADD A LEADING SLASH to the files. Doing so will lead to DANGER!
        """
        #Prepare the paths
        if not os.path.exists(image_path):
            logger.error("Could not find local image!")
            raise Exception("Image file not found")

        if not os.path.exists(mount_point):
            os.makedirs(mount_point)

        #Mount the directory
        out, err = mount_image(image_path, mount_point)
        if err:
            raise Exception("Encountered errors mounting the image: %s" % err)

        #Begin removing user-specified files (Matches wildcards)
        if exclude and exclude[0]:
            logger.info("User-initiated files to be removed: %s" % exclude)
            remove_files(exclude, mount_point)

        remove_user_data(mount_point)
        remove_atmo_data(mount_point)
        remove_vm_specific_data(mount_point)

        #Don't forget to unmount!
        run_command(['umount', mount_point])
        return

    def _bundle_image(self, image_path, destination_path, kernel=None,
                      ramdisk=None, user=None, target_arch='x86_64',
                      mapping=None, product_codes=None, ancestor_ami_ids=[]):
        """
        Takes a RAW image (image_path)
        Once finished, a new manifest and parts and creates a MANIFEST and PARTS

        bundle_image - Bundles an image given the correct params
        Required Params:
            image_path - Path to the image file
            kernel -  eki-###
            ramdisk - eri-###
        Optional Params:
            destination_path -
            (Default: /tmp) Path where the image,
            manifest, and parts file will reside
            target_arch - (Default: x86_64) Targeted Architecture of the image
            user -
            mapping  -
            product_codes  -
        """
        logger.debug('Bundling image from dir:%s' % destination_path)
        try:
            self.euca.validate_file(image_path)
        except FileValidationError:
            logger.error('Imaging process aborted. '
                         + 'Error: Image file not found!')
            raise

        cert_path = self.ec2_cert_path
        private_key_path = self.pk_path
        euca_cert_path = self.euca_cert_path
        try:
            self.euca.validate_file(cert_path)
            self.euca.validate_file(private_key_path)
            self.euca.validate_file(euca_cert_path)
        except FileValidationError:
            logger.error('Imaging process aborted. '
                         + 'Error: Eucalyptus files not found!'
                         + ' Did you source the admin self.eucarc?')
            raise
        except TypeError:
            logger.error("Image process aborted! Environment not properly set."
                         + " EC2_CERT, EC2_PRIVATE_KEY,"
                         + "or EUCALYPTUS_CERT not found!")
            raise

        #Verify the image
        logger.debug('Verifying image')
        image_size = self.euca.check_image(image_path, destination_path)
        prefix = self.euca.get_relative_filename(image_path)
        logger.debug('tarzip_image(%s,%s,%s)'
                     % (prefix, image_path, destination_path))
        #Tar the image file
        logger.debug('Zipping the image')
        (tgz_file, sha_image_digest) = self.euca.tarzip_image(
            prefix, image_path, destination_path)
        logger.debug('Encrypting zip file')
        (encrypted_file, key, iv, bundled_size) = self.euca.encrypt_image(
            tgz_file)
        os.remove(tgz_file)
        #Create the encrypted File
        logger.debug('Splitting image into parts')
        parts, parts_digest = self.euca.split_image(encrypted_file)
        #Generate manifest using encrypted file
        logger.debug('Generating manifest')
        self.euca.generate_manifest(
            destination_path, prefix, parts, parts_digest, image_path, key, iv,
            cert_path, euca_cert_path, private_key_path, target_arch, image_size,
            bundled_size, sha_image_digest, user, kernel, ramdisk, mapping,
            product_codes, ancestor_ami_ids)
        logger.debug('Manifest Generated')
        #Destroyed encrypted file
        os.remove(encrypted_file)
        manifest_loc =  os.path.join(destination_path, '%s.manifest.xml' %
                prefix)
        return manifest_loc

    def _export_to_s3(self, keyname,
                      the_file, bucketname='eucalyptus_exports',
                      **kwargs):
        s3_key = kwargs.get('s3_key')
        s3_secret = kwargs.get('s3_secret')
        s3_url = kwargs.get('s3_url')
        key = self._upload_file_to_s3(bucketname, keyname, the_file,
                                      s3_key, s3_secret, s3_url)
        #Key matches on basename of file
        url = key.generate_url(60*60*24*7)  # 7 days from now.
        return url

    def _upload_file_to_s3(self, bucket_name, keyname,
                           filename, s3_key, s3_secret,
                           s3_url, canned_acl='aws-exec-read'):
        s3euca = Euca2ool(is_s3=True)
        s3euca.ec2_user_access_key = s3_key
        s3euca.ec2_user_secret_key = s3_secret
        s3euca.url = s3_url

        conn = s3euca.make_connection()
        bucket_instance = _ensure_bucket(conn, bucket_name, canned_acl)
        k = Key(bucket_instance)
        k.key = keyname
        with open(filename, "rb") as the_file:
            try:
                logger.debug("Uploading File:%s to bucket:%s // key:%s"
                             % (filename, bucket_name, keyname))
                k.set_contents_from_file(the_file, policy=canned_acl)
                logger.debug("File Upload complete")
            except S3ResponseError, s3error:
                s3error_string = '%s' % (s3error)
                if s3error_string.find("403") >= 0:
                    logger.exception("Permission denied while writing : %s\n%s"
                                % (k.key, s3error))
        return k

    def _upload_bundle(self, bucket_name, manifest_path, ec2cert_path=None,
                       directory=None, part=None,
                       canned_acl='aws-exec-read', skipmanifest=False):
        """
        upload_bundle - Read the manifest and upload the entire bundle
        (In parts) to the S3 Bucket (bucket_name)

        Required Args:
            bucket_name - The name of the S3 Bucket to be created
            manifest_path - The absolute path to the XML manifest
        Optional Args:
            ec2cert_path = (Default:os.environ['EC2_CERT'])
            The absolute path to the Admin EC2 Cert (For S3 Access)
            canned_acl - (Default:'aws-exec-read')
            skipmanifest - (Default:False) Skip manifest upload
            directory - Select directory of parts
            (If different than values in XML)
            part -
        """
        from euca2ools import Euca2ool, FileValidationError
        logger.debug("Validating the manifest")
        try:
            self.euca.validate_file(manifest_path)
        except FileValidationError:
            print 'Invalid manifest'
            logger.error("Invalid manifest file provided. Check path")
            raise

        s3euca = Euca2ool(is_s3=True)
        s3euca.ec2_user_access_key = self.euca.ec2_user_access_key
        s3euca.ec2_user_secret_key = self.euca.ec2_user_secret_key
        s3euca.url = self.s3_url

        conn = s3euca.make_connection()
        bucket_instance = _ensure_bucket(conn, bucket_name, canned_acl)
        logger.debug("S3 Bucket %s Created. Retrieving Parts from manifest"
                     % bucket_name)
        parts = self._get_parts(manifest_path)
        if not directory:
            manifest_path_parts = manifest_path.split('/')
            directory = manifest_path.replace(
                manifest_path_parts[len(manifest_path_parts) - 1], '')
        if not skipmanifest and not part:
            _upload_manifest(bucket_instance, manifest_path, canned_acl)
        logger.debug("Uploading image in parts to S3 Bucket %s." % bucket_name)
        _upload_parts(bucket_instance, directory, parts, part, canned_acl)
        return "%s/%s" % \
            (bucket_name, self.euca.get_relative_filename(manifest_path))

    def _register_bundle(self, s3_manifest_path):
        try:
            logger.debug("Registering S3 manifest file:%s with image in euca"
                         % s3_manifest_path)
            euca_conn = self.euca.make_connection()
            image_id = euca_conn.register_image(
                image_location=s3_manifest_path)
            return image_id
        except Exception, ex:
            logger.error(ex)
            self.euca.display_error_and_exit('%s' % ex)

    def _build_instance_nc_map(self):
        """
        Using the 'DescribeNodes' API response,
        create a map with instance keys and node_controller_ip values:
            i-12341234 => 128.196.1.1
            i-12345678 => 128.196.1.2
        """
        boto_instances = self.image_conn.get_list(
            "DescribeNodes", {}, [('euca:item', BotoInstance)], '/')
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
    Indirect Download Image Functions
    These functions are called indirectly during the 'download_image' process.
    """
    def _unbundle_euca_image(self, image_location, download_dir, part_dir,
            pk_path):
        logger.debug("Complete. Begin Download of Image  @ %s.."
                     % datetime.now())
        (bucket_name, manifest_loc) = image_location.split('/')
        whole_image =  os.path.join(
            download_dir,
            manifest_loc.replace('.manifest.xml',''))
        if os.path.isfile(whole_image):
            # DONT re-download the file if it exists!
            logger.debug("Found image file: %s -- Skipping download"
                         % whole_image)
            return whole_image
        bucket = self.get_bucket(bucket_name)
        logger.debug("Bucket found : %s" % bucket)
        self._download_manifest(bucket, part_dir, manifest_loc)
        logger.debug("Manifest downloaded")
        part_list = self._download_parts(bucket, part_dir, manifest_loc)
        logger.debug("Image parts downloaded")
        whole_image = self._unbundle_manifest(part_dir, download_dir,
                                              os.path.join(part_dir,
                                                           manifest_loc),
                                              pk_path, part_list)
        logger.debug("Complete @ %s.." % datetime.now())
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
        for idx, part in enumerate(parts):
            part_loc = os.path.join(download_dir, part)
            part_files.append(part_loc)
            if os.path.exists(part_loc):
                #Do not re-download an existing part file
                continue
            part_file = open(part_loc, 'wb')
            k = Key(bucket)
            k.key = part
            if idx % 5 == 0:
                logger.debug("Downloading part %d/%d.." % (idx+1, len(parts)))
            k.get_contents_to_file(part_file)
            part_file.close()
        return part_files

    def _unbundle_manifest(self, source_dir, download_dir, manifest_file_loc,
                           pk_path, part_list=[]):
        #Determine # of parts in source_dir
        logger.debug("Preparing to unbundle downloaded image")
        (parts, encrypted_key, encrypted_iv) = self.euca.parse_manifest(
            manifest_file_loc)
        #Use euca methods to assemble parts
        #in source_dir to create encrypted .tar
        logger.debug("Manifest parsed")
        encrypted_image = self.euca.assemble_parts(source_dir, download_dir,
                                                   manifest_file_loc, parts)
        for part_loc in part_list:
            os.remove(part_loc)
        logger.debug("Encrypted image assembled")
        #Use the pk_path to unencrypt all information
        #using information provided from parsing the manifest
        #to create new .tar file
        tarred_image = self.euca.decrypt_image(encrypted_image, encrypted_key,
                                               encrypted_iv, pk_path)
        os.remove(encrypted_image)
        logger.debug("Image decrypted.. Untarring")
        image = self.euca.untarzip_image(download_dir, tarred_image)
        os.remove(tarred_image)
        logger.debug("Image untarred")
        return image
    """
    Generally Indirect functions - These are useful for
    debugging and gathering necessary info at the REPL
    """
    def list_buckets(self):
        return self.s3_conn.get_all_buckets()

    def find_bucket(self, name):
        return [b for b in self.list_buckets()
                if name.lower() in b.name.lower()]

    def get_bucket(self, bucket_name):
        return self.s3_conn.get_bucket(bucket_name)

    def list_instances(self):
        euca_conn = self.euca.make_connection()
        return euca_conn.get_all_instances()

    def find_instance(self, instance_id):
        for res in self.list_instances():
            for instance in res.instances:
                if instance_id.lower() in instance.id.lower():
                    return (res, instance)

    def list_images(self):
        euca_conn = self.euca.make_connection()
        return euca_conn.get_all_images()

    def find_image(self, name):
        return [m for m in self.list_images()
                if name.lower() in m.location.lower()]

    def get_image(self, image_id):
        euca_conn = self.euca.make_connection()
        image = euca_conn.get_image(image_id)
        #Believe it or not, this image may NOT be the one we requested.
        if image.id != image_id:
            return None
        return image

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
                bucket_instance = _create_bucket(
                    connection, bucket, canned_acl)
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


def _upload_parts(bucket_instance, directory, parts,
                  part_to_start_from, canned_acl=None):
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


