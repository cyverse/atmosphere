"""
ImageManager:
    Remote Eucalyptus Image management (euca2ools 1.3.1 + boto ec2)

Creating an Image from an Instance (Manual image requests)

>> from service.drivers.eucalyptusImageManager import ImageManager
>> manager = ImageManager()
>> manager.create_image('i-12345678', 'New image name v1')

Migrating an Instance/Image (Example: Eucalyptus --> Openstack)
>> manager.migrate_image('/temp/image/path/', 'emi-F1F122E4')
    _OR_
>> manager.migrate_instance('/temp/image/path/', 'i-12345678')

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

class ImageManager():
    """
    Convienence class that uses a combination of boto and euca2ools calls
    to remotely download an image form the cloud
    """
    s3_conn = None
    euca = None
    s3_url = None
    def __init__(self, key=settings.EUCA_ADMIN_KEY, secret=settings.EUCA_ADMIN_SECRET, 
                ec2_url=settings.EUCA_EC2_URL, s3_url=settings.EUCA_S3_URL, 
                ec2_cert_path=settings.EC2_CERT_PATH, pk_path=settings.EUCA_PRIVATE_KEY, 
                euca_cert_path=settings.EUCALYPTUS_CERT_PATH, 
                config_path='/services/Configuration'):
        """
        Will initialize with admin settings if no args are passed.
        Private Key file required to decrypt images.
        """
        self.euca = Euca2ool()
        if not key:
            key = os.environ['EC2_ACCESS_KEY']
        if not secret:
            secret = os.environ['EC2_SECRET_KEY']
        if not ec2_url:
            ec2_url = os.environ['EC2_URL']
        if not s3_url:
            s3_url = os.environ['S3_URL']
        if not ec2_cert_path:
            ec2_cert_path=os.environ['EC2_CERT']
        if not pk_path:
            pk_path=os.environ['EC2_PRIVATE_KEY']
        if not euca_cert_path:
            euca_cert_path=os.environ['EUCALYPTUS_CERT']

        self.euca.ec2_user_access_key=key
        self.euca.ec2_user_secret_key=secret
        self.euca.url = ec2_url
        self.s3_url = s3_url
        self.euca.environ['EC2_CERT'] = ec2_cert_path
        self.euca.environ['EUCALYPTUS_CERT'] = euca_cert_path
        self.euca.environ['EC2_PRIVATE_KEY'] = pk_path

        parsed_url = urlparse(s3_url)
        self.s3_conn = S3Connection(aws_access_key_id=key, aws_secret_access_key=secret, 
                                is_secure=('https' in parsed_url.scheme), 
                                host=parsed_url.hostname, port=parsed_url.port, 
                                path=parsed_url.path, 
                                calling_format=OrdinaryCallingFormat())

        parsed_url = urlparse(ec2_url)
        region = RegionInfo(None, 'eucalyptus', parsed_url.hostname)
        self.image_conn = connect_ec2(aws_access_key_id=key, aws_secret_access_key=secret, 
                                is_secure=False, region=region, 
                                port=parsed_url.port, path=config_path)
        self.image_conn.APIVersion = 'eucalyptus'

    def create_image(self, instance_id, image_name, public=True, 
                    private_user_list=[], exclude=[], kernel=None, 
                    ramdisk=None, meta_name=None, 
                    local_download_dir='/tmp', remote_img_path=None, keep_image=False):
        """
        Creates an image of a running instance
        Required Args:
            instance_id - The instance that will be imaged
            image_name - The name of the image 
        Optional Args (That are required for euca):
            public - Should image be accessible for other users? (Default: True)
            private_user_list  - List of users who should get access to the image (Default: [])
            kernel  - Associated Kernel for image (Default is instance.kernel)
            ramdisk - Associated Ramdisk for image (Default is instance.ramdisk)
        Optional Args:
            meta_name - Override the default naming convention
            local_download_dir - Override the default download dir (All files will be temporarilly stored here, then deleted
            remote_img_path - Override the default path to the image (On the Node Controller -- Must be exact to the image file (root) )
        """
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
        image_path = self._retrieve_local_image(instance_id, image_path, remote_img_path)
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

        return self._retrieve_local_image(instance_id, local_img_path, remote_img_path)
        
    def run_command(self, commandList, stdout=subprocess.PIPE, stderr=subprocess.PIPE):
        """
        Using Popen, run any command at the system level and record the output and error streams
        """
        out = None
        err = None
        logger.debug("Running Command:<%s>" % ' '.join(commandList))
        try:
            proc = subprocess.Popen(commandList, stdout=stdout, stderr=stderr)
            out,err = proc.communicate()
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

    def _retrieve_local_image(self, instance_id, local_img_path, remote_img_path):
        """
        Downloads image to local disk
        """
        #SCP remote file only if file does not exist locally
        if not os.path.exists(local_img_path):
            nodes = self._build_instance_nc_map()
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
        NOTE: no-password, SSH access to the node controller FROM THIS MACHINE is REQUIRED
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

        
    def _clean_local_image(self, image_path, mount_point, exclude=[]):
        """
        NOTE: When adding to this list, NEVER ADD A LEADING SLASH to the files. Doing so will lead to DANGER!
        """
        #Prepare the paths
        if not os.path.exists(image_path):
            logger.error("Could not find local image!")
            raise Exception("Image file not found")

        if not os.path.exists(mount_point):
            os.makedirs(mount_point)
        #Mount the directory
        self.run_command(['mount', '-o', 'loop', image_path, mount_point])

        #Patchfix
        self._readd_atmo_boot(mount_point)

        #Begin removing files
        for rm_file in exclude:
            if len(rm_file) == 0:
                continue
            if rm_file.startswith('/'):
                logger.warn("WARNING: File %s has a LEADING slash. This causes the changes to occur on the HOST MACHINE and must be changed!" % rm_file)
                rm_file = rm_file[1:]

            rm_file_path = os.path.join(mount_point,rm_file)
            #Expands the wildcard to test if the file(s) in question exist
            if glob.glob(rm_file_path):
                self.run_command(['/bin/rm', '-rf', rm_file_path])
        
        for rm_file in ['home/*', 'mnt/*', 'tmp/*', 'root/*', 'dev/*', 'proc/*', 'var/lib/puppet/run/*.pid', 'etc/puppet/ssl', 'usr/sbin/atmo_boot.py', 'var/log/atmo/atmo_boot.log', 'var/log/atmo/atmo_init.log']:
            if rm_file.startswith('/'):
                logger.warn("File %s has a LEADING slash. This causes the changes to occur on the HOST MACHINE and must be changed!" % rm_file)
                rm_file = rm_file[1:]

            rm_file_path = os.path.join(mount_point,rm_file)
            #Expands the wildcard to test if the file(s) in question exist
            if glob.glob(rm_file_path):
                self.run_command(['/bin/rm', '-rf', rm_file_path])

        #Copy /dev/null to clear sensitive logging data
        for overwrite_file in ['root/.bash_history', 'var/log/auth.log', 'var/log/boot.log', 'var/log/daemon.log', 'var/log/denyhosts.log', 'var/log/dmesg', 'var/log/secure', 'var/log/messages', 'var/log/lastlog', 'var/log/cups/access_log', 'var/log/cups/error_log', 'var/log/syslog', 'var/log/user.log', 'var/log/wtmp', 'var/log/atmo/atmo_boot.log', 'var/log/atmo/atmo_init.log', 'var/log/apache2/access.log', 'var/log/apache2/error.log', 'var/log/yum.log', 'var/log/atmo/puppet', 'var/log/puppet', 'var/log/atmo/atmo_init_full.log']:
            if overwrite_file.startswith('/'):
                logger.warn("File %s has a LEADING slash. This causes the changes to occur on the HOST MACHINE and must be changed!" % overwrite_file)
                overwrite_file = overwrite_file[1:]

            overwrite_file_path = os.path.join(mount_point,overwrite_file)
            if os.path.exists(overwrite_file_path):
                self.run_command(['/bin/cp', '-f', '/dev/null', '%s' % overwrite_file_path])

        #SED Replace sensitive user information
        for (replace_str, replace_with, replace_where) in [ ("\(users:x:100:\).*","users:x:100:","etc/group"),
                                                            ("AllowGroups users root.*","","etc/ssh/sshd_config") ]:
            replace_file_path = os.path.join(mount_point,replace_where)
            if os.path.exists(replace_file_path):
                self.run_command(["/bin/sed", "-i", "s/%s/%s/" % (replace_str, replace_with), replace_file_path])

        #Multi-line SED Replacement.. Equivilant of: DeleteFrom/,/DeleteTo / d <--Delete the regexp match
        for (delete_from, delete_to, replace_where) in [("## Atmosphere system","# End Nagios","etc/sudoers"), 
                                                        ("## Atmosphere","AllowGroups users core-services root","etc/ssh/sshd_config")]:
            replace_file_path = os.path.join(mount_point,replace_where)
            if os.path.exists(replace_file_path):
                self.run_command(["/bin/sed", "-i", "/%s/,/%s/d" % (delete_from, delete_to), replace_file_path])

        #Don't forget to unmount!
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
        for inst in boto_instances:
            if hasattr(inst, 'euca:name'):
                last_node = getattr(inst, 'euca:name')
            if not hasattr(inst, 'euca:entry'):
                continue
            instance_id = getattr(inst, 'euca:entry')
            nodes[instance_id] = last_node
        return nodes

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

