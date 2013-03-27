"""
Atmosphere service machine.

"""
from abc import ABCMeta

from core import Persist

from service.provider import AWSProvider, EucaProvider, OSProvider


class BaseMachine(Persist):
    __metaclass__ = ABCMeta


class Machine(BaseMachine):

    provider = None

    machines = {}

    lc_images = None

    def __init__(self, lc_image):
        self._image = lc_image
        self.id = lc_image.id
        self.alias = lc_image.id
        self.name = lc_image.name

    @classmethod
    def create_machine(cls, provider, lc_image):
        machine = provider.machineCls(lc_image)
        alias = machine.id
        cls.machines[(provider, alias)] = machine
        return machine

    @classmethod
    def get_machine(cls, lc_image):
        alias = lc_image.id
        if cls.machines.get((cls.provider, alias)):
            return cls.machines[(cls.provider, alias)]
        else:
            return cls.create_machine(cls.provider, lc_image)

    @classmethod
    def get_machines(cls, lc_list_images_method, *args, **kwargs):
        if not cls.machines or not cls.lc_images:
            cls.lc_images = lc_list_images_method(*args, **kwargs)
        return map(cls.get_machine, cls.lc_images)

    def load(self):
        raise NotImplemented

    def save(self):
        raise NotImplemented

    def delete(self):
        raise NotImplemented

    def reset(self):
        Machine.reset()
        self.machines = {}
        self.lc_images = None

    @classmethod  # order matters... /sigh
    def reset(cls):
        cls.machines = {}
        cls.lc_images = None

    def __unicode__(self):
        return str(self)

    def __str__(self):
        return reduce(
            lambda x, y: x+y,
            map(unicode, [self.__class__, " ", self.json()])
        )

    def __repr__(self):
        return str(self)

    def json(self):
        return {'id': self.id,
                'alias': self.alias,
                'name': self.name,
                'provider': self.provider.name}


class AWSMachine(Machine):

    provider = AWSProvider


class EucaMachine(Machine):

    provider = EucaProvider


class OSMachine(Machine):

    provider = OSProvider
