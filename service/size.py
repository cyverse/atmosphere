"""
Atmosphere service size.

"""
from abc import ABCMeta, abstractmethod

from core import Persist

from service.provider import AWSProvider, EucaProvider, OSProvider

class BaseSize(Persist):
    __metaclass__ = ABCMeta

class Size(BaseSize):

    provider = None

    sizes = {}

    lc_sizes = None

    def __init__(self, lc_size):
        self._size = lc_size
        self.id = lc_size.id
        if hasattr(self._size,'extra'):
            self.extra = self._size.extra
            if 'cpu' in self.extra:
                self.cpu = self.extra['cpu']
            else:
                self.cpu = 0
        else:
            self.cpu = 0

    @classmethod
    def create_size(cls, provider, lc_size):
        size = provider.sizeCls(lc_size)
        alias = size.id
        cls.sizes[(provider, alias)] = size
        return size

    @classmethod
    def get_size(cls, lc_size):
        alias = lc_size.id
        if cls.sizes.get((cls.provider, alias)):
            return cls.sizes[(cls.provider, alias)]
        else:
            return cls.create_size(cls.provider, lc_size)

    @classmethod
    def get_sizes(cls, lc_list_sizes_method):
        if not cls.sizes or not cls.lc_sizes:
            cls.lc_sizes = lc_list_sizes_method()
        return sorted(map(cls.get_size, cls.lc_sizes), key=lambda s: s._size.ram)

    def load(self):
        raise NotImplemented

    def save(self):
        raise NotImplemented

    def delete(self):
        raise NotImplemented

    def reset(self):
        Size.reset()
        self._size = None
        self.lc_sizes = None
        self.sizes = {}

    @classmethod
    def reset(cls):
        cls.lc_sizes = None
        cls.sizes = {}

    def __unicode__(self):
        return str(self)

    def __str__(self):
        return reduce(lambda x, y: x+y, map(unicode, [self.__class__, " ", self.json()]))

    def __repr__(self):
        return str(self)

    def json(self):
        return {
            'id' : self._size.name,
            'alias' : self._size.id,
            'name' : self._size.name,
            'cpu' : self.cpu,
            'ram' : self._size.ram,
            'disk' : self._size.disk,
            'bandwidth' : self._size.bandwidth,
            'price' : self._size.price
                }    

class EucaSize(Size):

    provider = EucaProvider

class AWSSize(Size):

    provider = AWSProvider

class OSSize(Size):

    provider = OSProvider
