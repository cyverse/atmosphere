"""
Atmosphere service machine.

"""
from abc import ABCMeta

from core import Persist

from service.provider import AWSProvider, EucaProvider, OSProvider


class BaseMachine():
    __metaclass__ = ABCMeta


class MockMachine(BaseMachine):

    def __init__(self, image_id, provider):
        self.id = image_id
        self.alias = image_id
        self.name = 'Unknown image %s' % image_id
        self._image = None
        self.provider = provider

    def json(self):
        return {'id': self.id,
                'alias': self.alias,
                'name': self.name,
                'provider': self.provider.name}


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
        cls.machines[(provider.name, alias)] = machine
        return machine

    @classmethod
    def get_machine(cls, lc_image):
        alias = lc_image.id
        if cls.machines.get((cls.provider.name, alias)):
            return cls.machines[(cls.provider.name, alias)]
        else:
            return cls.create_machine(cls.provider, lc_image)

    @classmethod
    def get_machines(cls, lc_list_images_method, *args, **kwargs):
        if not cls.machines or not cls.lc_images:
            cls.lc_images = lc_list_images_method(*args, **kwargs)
        return map(cls.get_machine, cls.lc_images)

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
