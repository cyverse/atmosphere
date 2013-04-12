"""
ImageManager:
    Remote Openstack Image management (euca2ools 1.3.1)

EXAMPLE USAGE:
from service.drivers.openstackImageManager import ImageManager
manager = ImageManager()
new_image = manager.upload_image("/home/esteve/images/wsgi_v3/sangeeta_esteve_DjangoWSGIStack-v3_11072012_105500.img", 'Django WSGI Stack')
In [4]: new_image
Out[4]: <Image {u'status': u'active', u'name': u'Django WSGI Stack',
    u'deleted': False, u'container_format': u'ovf', u'created_at':
    u'2012-11-20T20:35:01', u'disk_format': u'raw', u'updated_at':
    u'2012-11-20T20:37:01', u'id': u'07b745b1-a8ca-4751-afc0-35f524f332db',
    u'owner': u'4ceae82d4bd44fb48aa7f5fcd36bcc4e', u'protected': False,
    u'min_ram': 0, u'checksum': u'3849fe55340d5a75f077086b73c349e4',
    u'min_disk': 0, u'is_public': True, u'deleted_at': None, u'properties': {},
    u'size': 10067378176}>

"""


from atmosphere import settings
from atmosphere.logger import logger
from libcloud.compute.providers import get_driver
from libcloud.compute.types import Provider
from glanceclient import Client as GlanceClient
from novaclient.v1_1.client import Client as NovaClient


class ImageManager():
    """
    Convienence class that uses a combination of boto and euca2ools calls
    to remotely download an image from the cloud
    * See http://www.iplantcollaborative.org/Zku
      For more information on image management
    """
    glance = None
    nova = None
    driver = None

    def __init__(self, key=settings.OPENSTACK_ADMIN_KEY,
                 secret=settings.OPENSTACK_ADMIN_SECRET,
                 url=settings.OPENSTACK_AUTH_URL,
                 tenant=settings.OPENSTACK_ADMIN_TENANT,
                 region=settings.OPENSTACK_DEFAULT_REGION):
        """
        Will initialize with admin settings if no args are passed.
        Private Key file required to decrypt images.
        """
        OpenStack = get_driver(Provider.OPENSTACK)
        #TODO: There should be a better way, perhaps just auth w/ keystone..
        self.driver = OpenStack(key, secret, ex_force_auth_url=url,
                                ex_force_auth_version='2.0_password',
                                secure=("https" in url),
                                ex_tenant_name=tenant)
        self.driver.connection.service_region = region
        self.driver.list_sizes()
        auth_token = self.driver.connection.auth_token
        catalog = self.driver.connection.service_catalog._service_catalog
        glance_endpoint_dict = catalog['image']['glance']
        #print glance_endpoint_dict
        #Selects the first endpoint listed
        endpoint = glance_endpoint_dict.keys()[0]
        glance_endpoint = glance_endpoint_dict[endpoint][0]['publicURL']
        glance_endpoint = glance_endpoint.replace('/v1', '')
        logger.debug(auth_token)
        logger.debug(glance_endpoint)
        self.glance = GlanceClient('1',
                                   endpoint=glance_endpoint,
                                   token=auth_token)
        self.nova = NovaClient(key, secret,
                               tenant, url,
                               service_type="compute")
        self.nova.client.region_name = settings.OPENSTACK_DEFAULT_REGION


    def upload_euca_image(self, name, image, kernel=None, ramdisk=None):
        """
        Upload a euca image to glance..
            name - Name of image when uploaded to OpenStack
            image - File containing the image
            kernel - File containing the kernel
            ramdisk - File containing the ramdisk
        Requires 3 separate uploads for the Ramdisk, Kernel, and Image
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
        Defaults ovf/raw are correct for a eucalyptus .img file
        """
        new_meta = self.glance.images.create(name=name,
                                             container_format=container_format,
                                             disk_format=disk_format,
                                             is_public=is_public,
                                             properties=properties,
                                             data=open(download_loc))
        return new_meta

    def download_image(self, download_dir, image_id):
        raise NotImplemented("not yet..")

    def create_image(self, instance_id, name=None, **kwargs):
        metadata = kwargs
        if not name:
            name = 'Image of %s' % instance_id
        server = self.nova.servers.find(id=instance_id)
        return self.nova.servers.create_image(server, name, metadata)
