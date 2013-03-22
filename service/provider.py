"""
Atmosphere service provider.

"""

from abc import ABCMeta, abstractmethod

from libcloud.compute.providers import get_driver as lc_get_driver
from libcloud.compute.types import Provider as LProvider

from core import Persist
from core.models import get_or_create
from core.models.provider import Provider as CoreProvider
from core.models.provider import ProviderType as CoreProviderType

from service.drivers.openstack_driver import OpenStack_Esh_NodeDriver
from service.drivers.eucalyptus_driver import Eucalyptus_Esh_NodeDriver
from service.drivers.aws_driver import Esh_EC2NodeDriver
from atmosphere.logger import logger


def lc_provider_id(provider):
    """
    Get the libcloud Provider using our service provider.
    
    Return the libcloud.compute Provider value.
    """
    p = None
    try:
        p = LProvider.__dict__[provider.location]
    except Exception as e:
        logger.warn("Unable to find provider location: %s." % provider.location)
        raise ServiceException(e)
    return p


class BaseProvider(Persist):
    __metaclass__ = ABCMeta

    core_provider_type = None

    core_provider = None

    identity = None

    lc_driver = None

    options = {}

    location = ''

    name = ''

    identityCls = None

    instanceCls = None

    machineCls = None

    sizeCls = None

    @abstractmethod
    def __init__(self, *args, **kwargs):
        raise NotImplemented

    @abstractmethod
    def provider_id(self):
        raise NotImplemented

    @abstractmethod
    def set_options(self):
        raise NotImplemented

    @abstractmethod
    def get_driver(self, *args, **kwargs):
        raise NotImplemented

 
class Provider(BaseProvider):

    def __init__(self, *args, **kwargs):
        """
        Get or Create CoreProvider and CoreProviderType for this provider using
        args and kwargs and class defaults.
        """
        self.core_provider_type = get_or_create(CoreProviderType, name=self.name)
        self.core_provider = get_or_create(CoreProvider,
                                           type = self.core_provider_type,
                                           location = self.location)
        if kwargs.get('url', None):
          self.parse_url(kwargs['url'])

    def parse_url(self, url):
        '!BOO!'
        from urlparse import urlparse
        urlobj = urlparse(url)
        self.options['host'] = urlobj.hostname
        self.options['port'] = urlobj.port
        self.options['path'] = urlobj.path
        self.options['secure'] = urlobj.scheme == 'https'

    def provider_id(self):
        try:
            return lc_provider_id(self)
        except Exception as e:
            raise ServiceException(e)

    def load(self):
        self.core_provider_type = get_or_create(CoreProviderType, name=self.name)
        self.core_provider = get_or_create(CoreProvider,
                                           type = self.core_provider_type,
                                           location = self.location)
        return self

    def save(self):
        """
        This is for administrating Atmosphere.
        Generally this should not be used. It will save CoreProvider or
        CoreProviderType from the database.
        """
        self.core_provider_type.save()
        self.core_provider.save()
        return True

    def delete(self, core_models = False):
        """
        This is for administrating Atmosphere.
        Generally this should not be used. It will delete CoreProvider or
        CoreProviderType from the database if core_models is true.
        """
        if core_models:
            self.core_provider.delete()
            self.core_provider_type.delete()
        self.core_provider = None
        self.core_provider_type = None
        return True


class AWSProvider(Provider):

    name = 'Amazon EC2'

    location = 'EC2_US_EAST'

    @classmethod
    def set_meta(cls):
        from service.identity import AWSIdentity
        from service.machine import AWSMachine
        from service.instance import AWSInstance
        from service.size import AWSSize
        from service.volume import AWSVolume
        from service.meta import AWSMeta
        cls.identityCls = AWSIdentity
        cls.machineCls = AWSMachine
        cls.instanceCls = AWSInstance
        cls.sizeCls = AWSSize
        cls.volumeCls = AWSVolume
        cls.metaCls = AWSMeta

    def set_options(self):
        """
        Get provider specific options.
        
        Return provider specific options in a dict.
        """
        self.options = {} # clear the options
        self.options.update(self.identity.credentials) # was ... {c.key : c.value for c in self.identity.credentials.all()})
        return self.options

    def get_driver(self, identity):
        """
        Get the libcloud driver using our service identity.
        
        Return the libcloud.compute driver class.
        """
        self.identity = identity
        self.lc_driver = Esh_EC2NodeDriver # lc_get_driver(self.provider_id())
        self.set_options()
        return self.lc_driver(key=self.options['key'],
                           secret=self.options['secret'])


class AWSUSWestProvider(AWSProvider):

    location = 'EC2_US_WEST'


class AWSUSEastProvider(AWSProvider):

    location = 'EC2_US_EAST'


class EucaProvider(Provider):

    name = 'Eucalyptus'

    location = 'EUCALYPTUS' #This need to be in all caps to match lib cloud.

    @classmethod
    def set_meta(cls):
        from service.identity import EucaIdentity
        from service.machine import EucaMachine
        from service.instance import EucaInstance
        from service.size import EucaSize
        from service.volume import EucaVolume
        from service.meta import EucaMeta
        cls.identityCls = EucaIdentity
        cls.machineCls = EucaMachine
        cls.instanceCls = EucaInstance
        cls.sizeCls = EucaSize
        cls.volumeCls = EucaVolume
        cls.metaCls = EucaMeta
    def set_options(self):
        """
        Get provider specific credentials.
        
        Return any provider specific credentials in a dict.
        """
        self.options = { 'secure' : 'False',
                         'host' : '128.196.172.136',
                         'port' : 8773,
                         'path' : '/services/Eucalyptus' }
        self.options.update(self.identity.credentials) # was ... {c.key : c.value for c in self.identity.credentials.all()})
        return self.options
    
    def get_driver(self, identity):
        """
        Get the libcloud driver using our service identity.
        
        Return the libcloud.compute driver class.
        """
        self.identity = identity
        self.lc_driver = Eucalyptus_Esh_NodeDriver # lc_get_driver(self.provider_id())
        self.set_options()
        return self.lc_driver(key=self.options['key'],
                      secret=self.options['secret'],
                      secure=self.options['secure'] != 'False',
                      host=self.options['host'],
                      port=self.options['port'],
                      path=self.options['path'])


class OSProvider(Provider):

    name = 'OpenStack'

    location = 'OPENSTACK'

    @classmethod
    def set_meta(cls):
        from service.identity import OSIdentity
        from service.machine import OSMachine
        from service.instance import OSInstance
        from service.size import OSSize
        from service.volume import OSVolume
        from service.meta import OSMeta
        cls.identityCls = OSIdentity
        cls.machineCls = OSMachine
        cls.instanceCls = OSInstance
        cls.sizeCls = OSSize
        cls.volumeCls = OSVolume
        cls.metaCls = OSMeta

    def set_options(self):
        """
        Get provider specific options.
        
        Return provider specific options in a dict.
        """
        self.options = { 'secure': 'False',
                         'ex_force_auth_version': '2.0_password' }
        self.options.update(self.identity.credentials)
        return self.options
        
    def get_driver(self, identity):
        """
        Get the libcloud driver using our service identity.
        
        Return the libcloud.compute driver class.
        """
        self.identity = identity
        self.lc_driver = OpenStack_Esh_NodeDriver # lc_get_driver(self.provider_id())
        self.set_options()
        return self.lc_driver(key=self.options['key'],
                      secret=self.options['secret'],
                      secure=self.options['secure'] != 'False',
                      ex_force_auth_url=self.options['ex_force_auth_url'],
                      ex_force_auth_version=self.options['ex_force_auth_version'],
                      ex_tenant_name=self.options['ex_tenant_name'])


class OSValhallaProvider(OSProvider):
    
    region_name = "ValhallaRegion"

    def set_options(self):
        """
        """
        super(OSValhallaProvider, self).set_options()
        self.options['ex_force_auth_url'] = 'http://heimdall.iplantcollaborative.org:5000/v2.0'
        self.options.update(self.identity.credentials)

class OSMidgardProvider(OSProvider):

    region_name = "MidgardRegion"

    def set_options(self):
        """
        """
        super(OSMidgardProvider, self).set_options()
        self.options['ex_force_auth_url'] = 'http://hnoss.iplantcollaborative.org:5000/v2.0'
        self.options.update(self.identity.credentials)
