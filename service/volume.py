"""
Atmosphere service volume.

"""
from abc import ABCMeta

from threepio import logger

from core import Persist

from service.provider import AWSProvider, EucaProvider, OSProvider


class BaseVolume(Persist):
    __metaclass__ = ABCMeta


class Volume(BaseVolume):

    provider = None

    machine = None

    def __init__(self, lc_volume):
        self._volume = lc_volume
        self.id = lc_volume.id
        self.alias = lc_volume.id
        self.attachment_set = lc_volume.extra['attachmentSet']
        self.extra = lc_volume.extra
        self.name = lc_volume.name
        self.provider = self.provider
        self.size = lc_volume.size

    @classmethod
    def get_volumes(cls, volumes):
        return map(cls.provider.volumeCls, volumes)

    def load(self):
        raise NotImplemented

    def save(self):
        raise NotImplemented

    def delete(self):
        raise NotImplemented

    def reset(self):
        Volume.reset()
        self._volume = None
        self.machine = None

    @classmethod  # order matters... /sigh
    def reset(cls):
        cls._volume = None
        cls.machine = None

    def __unicode__(self):
        return str(self)

    def __str__(self):
        return reduce(
            lambda x, y: x+y, map(unicode, [self.__class__, " ", self.json()])
        )

    def __repr__(self):
        return str(self)

    def json(self):
        return {'id': self.id,
                'alias': self.alias,
                'attachment_set': self.attachment_set,
                'extra': self.extra,
                'name': self.name,
                'provider': self.provider.name,
                'size': self.size}


class AWSVolume(Volume):

    provider = AWSProvider


class EucaVolume(Volume):

    provider = EucaProvider


class OSVolume(Volume):

    provider = OSProvider
