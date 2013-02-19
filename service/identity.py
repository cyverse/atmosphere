"""
Atmosphere service identity.

"""
from abc import ABCMeta, abstractmethod

from atmosphere.logger import logger

from core import Persist
from core.exceptions import MissingArgsException

from service.provider import AWSProvider, EucaProvider, OSProvider

class BaseIdentity(Persist):
    __metaclass__ = ABCMeta
    
    core_identity = None

    provider = None

    groups = [] 
    providers = [] 
    machines = [] 
    instances = [] 

    credentials = {}

    @abstractmethod
    def __init__(self, provider, user, key, secret):
        raise NotImplemented

class Identity(BaseIdentity):
    
    def __init__(self, provider, key, secret, user=None, **kwargs):
        if provider is Provider:
            self.providers.add(provider) # Add it if it's not already added.
        else:
            raise MissingArgsException('Provider is bad.')
        self.user = user
        self.credentials.update(kwargs)
        self.credentials.update({ 'key' : key, 'secret' : secret })

    def load(self):
        user_wrap = UserWrapper(self.user, self.provider.core_provider)
        machines = user_wrap.all_machines()
        instances = user_wrap.all_instances()
        groups = user_wrap.all_groups()

    def save(self):
        self.ProviderType.save()
        self.Provider.save()
        self.Identity.save()
        map(save, self.credentials)
        return True

    def delete(self):
        map(delete, self.credentials)
        self.credentials.clear()
        self.credentials = { 'provider_type' : None,
                        'provider' : None}
        self.Identity.delete()
        return True

class EshIdentity(Identity):

    def __init__(self, provider, key, secret, user=None, **kwargs):

        if issubclass(type(provider), self.provider):
            self.providers.append(provider)
        else:
            logger.warn ("Provider doesn't match (%s != %s)." % (provider, self.provider))
#            raise MissingArgsException('Provider is bad.')
        self.user = user
        self.credentials.update(kwargs)
        self.credentials.update({ 'key' : key, 'secret' : secret })

class AWSIdentity(EshIdentity):

    provider = AWSProvider

class EucaIdentity(EshIdentity):

    provider = EucaProvider

class OSIdentity(EshIdentity):

    provider = OSProvider

