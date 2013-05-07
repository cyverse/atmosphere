"""
Atmosphere service meta.

"""
import sys

from abc import ABCMeta

from threepio import logger

from atmosphere import settings

from service.provider import AWSProvider, EucaProvider, OSProvider,\
    OSValhallaProvider
from service.identity import AWSIdentity, EucaIdentity, OSIdentity
from service.driver import AWSDriver, EucaDriver, OSDriver
from service.linktest import active_instances

from core.models import Identity
from service.accounts.openstack import AccountDriver as OSAccountDriver

class BaseMeta(object):
    __metaclass__ = ABCMeta


class Meta(BaseMeta):

    provider = None

    metas = {}

    def __init__(self, driver):
        self._driver = driver._connection
        self.user = driver.identity.user
        self.provider = driver.provider
        self.identity = driver.identity
        self.driver = driver
        self.admin_driver = self.create_admin_driver()

    @classmethod
    def create_meta(cls, driver):
        meta = driver.provider.metaCls(driver)
        cls.metas[(driver.provider, driver.identity)] = meta
        return meta

    @classmethod
    def get_meta(cls, driver):
        id = (cls.provider, driver.identity)
        if cls.metas.get(id):
            return cls.metas[id]
        else:
            return cls.create_meta(driver)

    @classmethod
    def get_metas(cls):
        super_metas = {}
        map(super_metas.update, [AWSProvider.metaCls.metas,
                                 EucaProvider.metaCls.metas,
                                 OSProvider.metaCls.metas])
        return super_metas

    def test_links(self):
        return active_instances(self.driver.list_instances())

    def create_admin_driver(self):
        raise NotImplementedError

    def all_instances(self):
        return self.provider.instanceCls.get_instances(
            self.admin_driver._connection.ex_list_all_instances())

    def reset(self):
        Meta.reset()
        self.metas = {}

    @classmethod  # order matters... /sigh
    def reset(cls):
        cls.metas = {}

    def __unicode__(self):
        return str(self)

    def __str__(self):
        return reduce(lambda x, y: x+y, map(unicode, [self.__class__,
                                                      " ",
                                                      self.json()]))

    def __repr__(self):
        return str(self)

    def json(self):
        return {'driver': self.driver,
                'identity': self.identity,
                'provider': self.provider.name}


class AWSMeta(Meta):

    provider = AWSProvider

    def create_admin_driver(self):
        if not hasattr(settings, 'AWS_KEY'):
            return self.driver
        logger.debug(self.provider)
        logger.debug(type(self.provider))
        identity = AWSIdentity(self.provider,
                               settings.AWS_KEY,
                               settings.AWS_SECRET)
        driver = AWSDriver(self.provider, identity)
        return driver

    def all_instances(self):
        return self.admin_driver.list_instances()


class EucaMeta(Meta):

    provider = EucaProvider

    def create_admin_driver(self):
        identity = EucaIdentity(self.provider,
                                settings.EUCA_ADMIN_KEY,
                                settings.EUCA_ADMIN_SECRET)
        driver = EucaDriver(self.provider, identity)
        return driver

    def occupancy(self):
        return self.admin_driver.list_sizes()

    def all_instances(self):
        return self.admin_driver.list_instances()


class OSMeta(Meta):

    provider = OSProvider

    def create_admin_driver(self):
        admin_provider = OSProvider()
        admin_identity = OSIdentity(admin_provider,
                                    settings.OPENSTACK_ADMIN_KEY,
                                    settings.OPENSTACK_ADMIN_SECRET,
                                    ex_tenant_name=
                                    settings.OPENSTACK_ADMIN_TENANT)
        admin_driver = OSDriver(admin_provider, admin_identity)
        return admin_driver

    def occupancy(self):
        """
        Add Occupancy data to NodeSize.extra
        """
        occupancy_data = self.admin_driver._connection.ex_hypervisor_statistics()
        all_instances = self.all_instances()
        sizes = self.admin_driver.list_sizes()
        for size in sizes:
            max_by_cpu = float(occupancy_data['vcpus'])/float(size.cpu)\
                if size._size.ram > 0\
                else sys.maxint

            max_by_ram = float(occupancy_data['memory_mb']) / \
                float(size._size.ram)\
                if size._size.ram > 0\
                else sys.maxint

            max_by_disk = float(occupancy_data['local_gb']) / \
                float(size._size.disk)\
                if size._size.disk > 0\
                else sys.maxint

            limiting_value = int(min(
                max_by_cpu,
                max_by_ram,
                max_by_disk))
            num_running = len([i for i in all_instances
                               if i.extra['flavorId'] == size.id])
            if not 'occupancy' in size.extra:
                size.extra['occupancy'] = {}
            size.extra['occupancy']['total'] = limiting_value
            size.extra['occupancy']['remaining'] = limiting_value - num_running
        return sizes

    def add_metadata_deployed(self, machine):
        """
        Add {"deployed": "True"} key and value to the machine's metadata.
        """
        machine_metadata = self.admin_driver._connection.ex_get_image_metadata(machine)
        machine_metadata["deployed"] = "True"
        self.admin_driver._connection.ex_set_image_metadata(machine, machine_metadata)

    def remove_metadata_deployed(self, machine):
        """
        Remove the {"deployed": "True"} key and value from the machine's
        metadata, if it exists.
        """
        machine_metadata = self.admin_driver._connection.ex_get_image_metadata(machine)
        if machine_metadata.get("deployed"):
            self.admin_driver._connection.ex_delete_image_metadata(machine, "deployed")

    def stop_all_instances(self, destroy=False):
        """
        Stop all instances and delete tenant networks for all users.

        To destroy instances instead of stopping them use the destroy
        keyword (destroy=True).
        """
        for instance in self.all_instances():
            if destroy:
                self.admin_driver.destroy_instance(instance)
                logger.debug('Destroyed instance %s' % instance)
            else:
                if instance.get_status() == 'active':
                    self.admin_driver.stop_instance(instance)
                    logger.debug('Stopped instance %s' % instance)
        os_driver = OSAccountDriver()
        if destroy:
            for username in os_driver.list_usergroup_names():
                tenant_name = username
                os_driver.network_manager.delete_tenant_network(username,
                                                            tenant_name)
        return True

    def destroy_all_instances(self):
        """
        Destroy all instances and delete tenant networks for all users.
        """
        for instance in self.all_instances():
            self.admin_driver.destroy_instance(instance)
            logger.debug('Destroyed instance %s' % instance)
        os_driver = OSAccountDriver()
        for username in os_driver.list_usergroup_names():
            tenant_name = username
            os_driver.network_manager.delete_tenant_network(username,
                                                            tenant_name)
        return True

    def all_instances(self):
        return self.provider.instanceCls.get_instances(
            self.admin_driver._connection.ex_list_all_instances())

    def all_volumes(self):
        return self.provider.instanceCls.get_instances(
            self.admin_driver._connection.ex_list_all_instances())
