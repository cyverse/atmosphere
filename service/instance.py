"""
Atmosphere service instance.

"""
from atmosphere.logger import logger

from core import Persist

from service.provider import AWSProvider, EucaProvider, OSProvider
from service.machine import Machine
from service.size import Size


class Instance(Persist):

    provider = None

    machine = None

    size = None

    def __init__(self, node):
        self._node = node
        self.id = node.id
        self.alias = node.id
        self.name = node.name
        self.image_id = node.extra['imageId']
        self.extra = node.extra
        self.ip = self.get_public_ip()
        if Machine.machines.get((self.provider.name, self.image_id)):
            self.machine = Machine.machines[(self.provider.name, self.image_id)]
        #else:
            #logger.info('Could not find the provider-machine (%s,%s)' %
            #            (self.provider, self.image_id))

    @classmethod
    def get_instances(cls, nodes):
        return map(cls.provider.instanceCls, nodes)

    def get_public_ip(self):
        raise NotImplementedError()

    def get_status(self):
        raise NotImplementedError()

    def load(self):
        raise NotImplementedError()

    def save(self):
        raise NotImplementedError()

    def delete(self):
        raise NotImplementedError()

    def reset(self):
        self._node = None

    def __unicode__(self):
        return str(self)

    def __str__(self):
        return reduce(
            lambda x, y: x+y,
            map(unicode, [self.__class__, " ", self.json()]))

    def __repr__(self):
        return str(self)

    def json(self):
        return {'id': self.id,
                'alias': self.alias,
                'name': self.name,
                'ip': self.ip,
                'provider': self.provider.name,
                'size': self.size.json(),
                'machine': self.machine.json()}


class AWSInstance(Instance):

    provider = AWSProvider

    def __init__(self, node):
        Instance.__init__(self, node)
        self.size = node.extra['instancetype']
        if Size.sizes.get((self.provider, self.size)):
            self.size = Size.sizes[(self.provider, self.size)]

    def get_public_ip(self):
        if self.extra \
           and self.extra.get('dns_name'):
            return self.extra['dns_name']


class EucaInstance(AWSInstance):

    provider = EucaProvider

    def get_public_ip(self):
        if self.extra:
            return self.extra.get('dns_name')

    def get_status(self):
        """
        """
        status = "Unknown"
        if self.extra \
           and self.extra.get('status'):
            status = self.extra['status']
        return status

class OSInstance(Instance):

    provider = OSProvider

    def __init__(self, node):
        Instance.__init__(self, node)
        if not self.machine:
            image = node.driver.ex_get_image(node.extra['imageId'])
            self.machine = self.provider.machineCls.get_machine(image)
        if not self.size:
            size = node.driver.ex_get_size(node.extra['flavorId'])
            self.size = self.provider.sizeCls.get_size(size)

    def get_public_ip(self):
        public_ips = self.get_public_ips()
        if not public_ips:
            return None
        return public_ips[0]

    def get_public_ips(self):
        #Get a list of all address spaces
        addresses = getattr(self, 'extra', {}).get('addresses',[])
        public_ips = []
        for addr_name,ips in addresses.items():
            for ip_addr in ips:
                if ip_addr['OS-EXT-IPS:type'] == 'floating':
                        public_ips.append(ip_addr['addr'])
        return public_ips

    def get_status(self):
        """
        TODO: If openstack: Use extra['task'] and extra['power']
        to determine the appropriate status.
        """
        status = "Unknown"
        if self.extra \
           and self.extra.get('status'):
            status = self.extra['status']
            task = self.extra.get('task')
            if task:
                status += ' - %s' % self.extra['task']
        return status
