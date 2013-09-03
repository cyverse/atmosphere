"""
ImageManager:
    Remote Openstack Image management (euca2ools 1.3.1)

EXAMPLE USAGE:
from service.imaging.drivers.openstack import ImageManager

from atmosphere import settings

manager = ImageManager(**settings.OPENSTACK_ARGS)

manager.create_image('75fdfca4-d49d-4b2d-b919-a3297bc6d7ae', 'my new name')

"""
import os
import time

from threepio import logger

from rtwo.driver import OSDriver
from rtwo.drivers.common import _connect_to_keystone, _connect_to_nova,\
                                   _connect_to_glance, find

from service.deploy import freeze_instance, sync_instance
from service.tasks.driver import deploy_to
from service.imaging.common import run_command, wildcard_remove
from service.imaging.clean import remove_user_data, remove_atmo_data,\
                                  remove_vm_specific_data
from service.imaging.common import unmount_image, mount_image, remove_files,\
                                    fsck_qcow, get_latest_ramdisk
from keystoneclient.exceptions import NotFound

class ImageManager():
    """
    Convienence class that uses a combination of boto and euca2ools calls
    to remotely download an image from the cloud
    * See http://www.iplantcollaborative.org/Zku
      For more information on image management
    """
    glance = None
    nova = None
    keystone = None

    @classmethod
    def lc_driver_init(self, lc_driver, *args, **kwargs):
        lc_driver_args = {
            'username': lc_driver.key,
            'password': lc_driver.secret,
            'tenant_name': lc_driver._ex_tenant_name,
            'auth_url': lc_driver._ex_force_auth_url,
            'region_name': lc_driver._ex_force_service_region
        }
        lc_driver_args.update(kwargs)
        manager = ImageManager(*args, **lc_driver_args)
        return manager

    def __init__(self, *args, **kwargs):
        if len(args) == 0 and len(kwargs) == 0:
            raise KeyError("Credentials missing in __init__. ")


        self.admin_driver = OSDriver.settings_init()
        self.keystone, self.nova, self.glance = self.new_connection(*args, **kwargs)

    def new_connection(self, *args, **kwargs):
        """
        Can be used to establish a new connection for all clients
        """
        keystone = _connect_to_keystone(*args, **kwargs)
        nova = _connect_to_nova(*args, **kwargs)
        glance = _connect_to_glance(keystone, *args, **kwargs)
        return (keystone, nova, glance)

    def list_servers(self):
        return [server for server in
                self.nova.servers.list(search_opts={'all_tenants':1})]

    def get_instance(self, instance_id):
        instances = self.admin_driver._connection.ex_list_all_instances()
        for inst in instances:
            if inst.id == instance_id:
                return inst
        return None

    def get_server(self, server_id):
        servers = [server for server in
                self.nova.servers.list(search_opts={'all_tenants':1}) if
                server.id == server_id]
        if not servers:
            return None
        return servers[0]

    def create_snapshot(self, instance_id, name, **kwargs):
        metadata = kwargs
        server = self.get_server(instance_id)
        if not server:
            raise Exception("Server %s does not exist" % instance_id)
        #self.prepare_snapshot(instance_id)
        logger.debug("Instance is prepared to create a snapshot")
        snapshot_id = self.nova.servers.create_image(server, name, metadata)

        #Step 2: Wait (Exponentially) until status moves from:
        # queued --> saving --> active
        attempts = 0
        while True:
            snapshot = self.get_image(snapshot_id)
            if attempts >= 40:
                break
            if snapshot.status is 'active':
                break
            attempts += 1
            logger.debug("Snapshot %s in non-active state %s" % (snapshot_id, snapshot.status))
            logger.debug("Attempt:%s, wait 1 minute" % attempts)
            time.sleep(60)
        if snapshot.status is not 'active':
            raise Exception("Create_snapshot timeout. Operation exceeded 40m")
        return snapshot

    def create_image(self, instance_id, name,
                     local_download_dir='/tmp',
                     exclude=None,
                     snapshot_id=None,
                     **kwargs):
        #Step 1: Build the snapshot
        ss_name = 'TEMP_SNAPSHOT <%s>' % name
        if not snapshot_id:
            snapshot = self.create_snapshot(instance_id, ss_name, **kwargs)
        else:
            snapshot = self.get_image(snapshot_id)
        #Step 3: Download local copy of the image
        server = self.get_server(instance_id)
        tenant = find(self.keystone.tenants, id=server.tenant_id)
        local_user_dir = os.path.join(local_download_dir, tenant.name)
        if not os.path.exists(local_user_dir):
            os.makedirs(local_user_dir)
        local_image = os.path.join(local_user_dir, '%s.qcow2' % name)
        logger.debug("Snapshot downloading to %s" % local_image)
        with open(local_image,'w') as f:
            for chunk in snapshot.data():
                f.write(chunk)
        logger.debug("Snapshot downloaded to %s" % local_image)
        #Step 4: Clean the local image
        fsck_qcow(local_image)
        self.clean_local_image(
                local_image,
                os.path.join(local_user_dir, 'mount/'),
                exclude=exclude)

        #Step 5: Upload the local copy as a 'real' image
        prev_kernel = snapshot.properties['kernel_id']
        prev_ramdisk = snapshot.properties['ramdisk_id']
        new_image = self.upload_image(local_image, name, 'ami', 'ami', True, {
            'kernel_id': prev_kernel,
            'ramdisk_id': prev_ramdisk})
        #TODO: Step 6: Verify the image works
        #TODO: Step 7: Delete the snapshot
        return new_image.id

    def prepare_snapshot(self, instance_id):
        kwargs = {}
        private_key = "/opt/dev/atmosphere/extras/ssh/id_rsa"
        kwargs.update({'ssh_key': private_key})
        kwargs.update({'timeout': 120})

        si_script = sync_instance()
        kwargs.update({'deploy': si_script})

        instance = self.get_instance(instance_id)
        self.admin_driver.deploy_to(instance, **kwargs)

        fi_script = freeze_instance()
        kwargs.update({'deploy': fi_script})
        deploy_to.delay(
            driver.__class__, driver.provider, dirver.identity, 
            instance)
        #Give it a head-start..
        time.sleep(1)

    def clean_local_image(self, image_path, mount_point, exclude=[]):
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
        unmount_image(image_path, mount_point)
        return

    def delete_images(self, image_id=None, image_name=None):
        if not image_id and not image_name:
            raise Exception("delete_image expects image_name or image_id as keyword"
            " argument")

        if image_name:
            images = [img for img in self.list_images()
                      if image_name in img.name]
        else:
            images = [self.glance.images.get(image_id)]

        if len(images) == 0:
            return False
        for image in images:
            self.glance.images.delete(image)

        return True

    def list_images(self):
        return self.nova.images.list()

    def get_image_by_name(self, name):
        for img in self.glance.images.list():
            if img.name == name:
                return img
        return None

    #Image sharing
    def shared_images_for(self, tenant_name=None, image_name=None):
        """

        @param can_share
        @type Str
        If True, allow that tenant to share image with others
        """
        if tenant_name:
            tenant = self.find_tenant(tenant_name)
            return self.glance.image_members.list(member=tenant)
        if image_name:
            image = self.find_image(image_name)
            return self.glance.image_members.list(image=image)

    def share_image(self, image, tenant_id, can_share=False):
        """

        @param can_share
        @type Str
        If True, allow that tenant to share image with others
        """
        return self.glance.image_members.create(
                    image, tenant_id, can_share=can_share)

    def unshare_image(self, image, tenant_id):
        tenant = find(self.keystone.tenants, name=tenant_name)
        return self.glance.image_members.delete(image.id, tenant.id)

    #Alternative image uploading
    def upload_euca_image(self, name, image, kernel=None, ramdisk=None):
        """
        Upload a euca image to glance..
            name - Name of image when uploaded to OpenStack
            image - File containing the image
            kernel - File containing the kernel
            ramdisk - File containing the ramdisk
        Requires 3 separate filepaths to uploads the Ramdisk, Kernel, and Image
        This is useful for migrating from Eucalyptus/AWS --> Openstack
        """
        opts = {}
        if kernel:
            new_kernel = self.upload_image(kernel,
                                           'eki-%s' % name,
                                           'aki', 'aki', True)
            opts['kernel_id'] = new_kernel.id
        if ramdisk:
            new_ramdisk = self.upload_image(ramdisk,
                                            'eri-%s' % name,
                                            'ari', 'ari', True)
            opts['ramdisk_id'] = new_ramdisk.id
        new_image = self.upload_image(image, name, 'ami', 'ami', True, opts)
        return new_image

    def upload_image(self, download_loc, name,
                     container_format='ovf',
                     disk_format='raw',
                     is_public=True, properties={}):
        """
        Upload a single file as a glance image
        Defaults ovf/raw are correct for a eucalyptus .img file
        """
        new_meta = self.glance.images.create(name=name,
                                             container_format=container_format,
                                             disk_format=disk_format,
                                             is_public=is_public,
                                             properties=properties,
                                             data=open(download_loc))
        return new_meta

    def download_image(self, download_dir, image_id, extension='raw'):
        image = self.glance.images.get(image_id)
        download_to = os.path.join(download_dir, '%s.%s' %
                                   (image_id,extension))
        #These lines are failing, look into it later..
        #with open(download_to, 'w') as imgf:
        #    imgf.writelines(image.data())
        #return download_to
        raise Exception("download_image is not supported at this time")

    #Lists
    def admin_list_images(self):
        """
        These images have an update() function
        to update attributes like public/private, min_disk, min_ram

        NOTE: glance.images.list() returns a generator, we return lists
        """
        return [i for i in self.glance.images.list()]

    def list_images(self):
        return [img for img in self.glance.images.list()]

    #Finds
    def get_image(self, image_id):
        found_images = [i for i in self.glance.images.list() if
                i.id == image_id]
        if not found_images:
            return None
        return found_images[0]

    def find_image(self, image_name, contains=False):
        return [i for i in self.glance.images.list() if
                i.name == image_name or
                (contains and image_name in i.name)]

    def find_tenant(self, tenant_name):
        try:
            tenant = find(self.keystone.tenants, name=tenant_name)
            return tenant
        except NotFound:
            return None
