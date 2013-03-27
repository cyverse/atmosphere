"""
Atmosphere service meta.

"""
from abc import ABCMeta

from atmosphere.logger import logger


from atmosphere import settings

from service.provider import AWSProvider, EucaProvider, OSProvider
from service.identity import AWSIdentity, EucaIdentity, OSIdentity
from service.driver import AWSDriver, EucaDriver, OSDriver
from service.linktest import active_instances


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
        occupancy = self.admin_driver._connection.ex_hypervisor_statistics()
        return occupancy

    def all_instances(self):
        return self.provider.instanceCls.get_instances(
            self.admin_driver._connection.ex_list_all_instances())
