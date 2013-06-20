"""
ImageManager:
    Remote Openstack Image management (euca2ools 1.3.1)

EXAMPLE USAGE:
from service.drivers.openstackImageManager import ImageManager

from atmosphere import settings

manager = ImageManager(**settings.OPENSTACK_ARGS)

manager.create_image('75fdfca4-d49d-4b2d-b919-a3297bc6d7ae', 'my new name')

"""

from threepio import logger

from service.driver import OSDriver
from service.drivers.common import _connect_to_keystone, _connect_to_nova,\
                                   _connect_to_glance, find
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

    def create_image(self, instance_id, name=None, **kwargs):
        """
        Creates a SNAPSHOT, not an image!
        """
        metadata = kwargs
        if not name:
            name = 'Image of %s' % instance_id
        servers = [server for server in
                self.nova.servers.list(search_opts={'all_tenants':1}) if
                server.id == instance_id]
        if not servers:
            return None
        server = servers[0]
        return self.nova.servers.create_image(server, name, metadata)

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
