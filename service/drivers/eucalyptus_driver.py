"""
Extension of libcloud's Eucalyptus Node Driver.
"""
import re
import string
from datetime import datetime

from libcloud.utils.xml import fixxpath, findall, findtext, findattr
from libcloud.compute.base import NodeSize, StorageVolume, NodeImage
from libcloud.compute.drivers.ec2 import EucNodeDriver, NAMESPACE

from threepio import logger


class Eucalyptus_Esh_NodeDriver(EucNodeDriver):
    """
    Eucalyptus 2.x node driver for esh.
    """

    def _is_name(self, name):
        for n in ['admin', 'edwins', 'edwin',
                  'esteve', 'jmatt', 'nirav',
                  'nmatasci', 'sangeeta', 
                  'sgregory', 'aedmonds']:
            if n == name:
                return name
        return False

    def _split_name(self, machine_name):
        split = machine_name.split('_')
        length = len(split)
        names = []
        for i in range(length):
            name = split[i]
            if self._is_name(name):
                names.append(name)
            else:
                return (names, ' '.join(split[i:length]))
        return ([], machine_name)

    def _drop_numbers(self, machine_name):
        return '_'.join(filter(lambda x:
                               not str.isdigit(x),
                               machine_name.split('_')))

    def _drop_filetype(self, machine_name):
        new_machine_name = machine_name.replace('.manifest.xml', '')
        return new_machine_name.replace('.img', '')

    def _drop_dir(self, machine_name):
        return machine_name.split('/')[1]

    def parse_machine_name(self, machine_name):
        new_machine_name = self._drop_numbers(
            self._drop_filetype(self._drop_dir(machine_name)))
        names, new_machine_name = self._split_name(new_machine_name)
        #logger.debug('%s->%s' % (machine_name,new_machine_name))
        #logger.debug('names = %s' % names)
        return new_machine_name

    def list_images(self, location=None, ex_image_ids=None, emi_only=True):
        """
        Ignore any ramdisks/kernels, unless set explicitly
        """
        image_list = super(Eucalyptus_Esh_NodeDriver, self).list_images(
            location, ex_image_ids)
        if emi_only:
            image_list = [img for img in image_list
                          if 'eri' not in img.id and 'eki' not in img.id]
        return image_list

    def _to_image(self, element):
        n = NodeImage(
            id=findtext(element=element, xpath='imageId', namespace=NAMESPACE),
            name=self.parse_machine_name(findtext(element=element,
                                                  xpath='imageLocation',
                                                  namespace=NAMESPACE)),
            driver=self.connection.driver,
            extra={
                'state': findattr(element=element, xpath="imageState",
                                  namespace=NAMESPACE),
                'ownerid': findattr(element=element, xpath="imageOwnerId",
                                    namespace=NAMESPACE),
                'owneralias': findattr(element=element,
                                       xpath="imageOwnerAlias",
                                       namespace=NAMESPACE),
                'ispublic': findattr(element=element,
                                     xpath="isPublic",
                                     namespace=NAMESPACE),
                'architecture': findattr(element=element,
                                         xpath="architecture",
                                         namespace=NAMESPACE),
                'imagetype': findattr(element=element,
                                      xpath="imageType",
                                      namespace=NAMESPACE),
                'platform': findattr(element=element,
                                     xpath="platform",
                                     namespace=NAMESPACE),
                'kernelid': findattr(element=element,
                                     xpath="kernelId",
                                     namespace=NAMESPACE),
                'ramdiskid': findattr(element=element,
                                      xpath="ramdiskId",
                                      namespace=NAMESPACE),
                'rootdevicetype': findattr(element=element,
                                           xpath="rootDeviceType",
                                           namespace=NAMESPACE),
                'virtualizationtype': findattr(
                    element=element, xpath="virtualizationType",
                    namespace=NAMESPACE),
                'hypervisor': findattr(element=element,
                                       xpath="hypervisor",
                                       namespace=NAMESPACE)
            }
        )
        return n

    def _to_node(self, api_node, groups=None, owner=None):
        def _set_ips(node):
            """
            Set up ips in the return node after _to_node calls it's super.
            """
            pass
            node.public_ips.append(node.extra.get('dns_name', '0.0.0.0'))
            node.private_ips.append(node.extra.get('private_dns', '0.0.0.0'))
            return node
        node = super(Eucalyptus_Esh_NodeDriver, self)._to_node(api_node,
                                                               groups)
        if owner:
            node.extra['ownerId'] = owner
        node = _set_ips(node)
        return node

    def _get_attachment_set(self, element):
        attachment_set = {}
        for elem in element:
            for key in ['volumeId', 'instanceId', 'device',
                        'status', 'attachTime']:
                value = findtext(element=elem, xpath=key, namespace=NAMESPACE)
                if value:
                    attachment_set[key] = value
        if attachment_set.get('attachTime', None):
            if '.' in attachment_set['attachTime']:
                attach_date = datetime.strptime(attachment_set['attachTime'],
                                                '%Y-%m-%dT%H:%M:%S.%fZ')
            else:
                attach_date = datetime.strptime(attachment_set['attachTime'],
                                                '%Y-%m-%dT%H:%M:%SZ')
            attachment_set['attachTime'] = attach_date
        return attachment_set

    def _to_volume(self, element, name=None):
        element_as = findall(element=element,
                             xpath='attachmentSet/item', namespace=NAMESPACE)
        volume = {}
        for key in ['volumeId', 'size', 'createTime',
                    'status', 'attachmentSet']:
            volume[key] = findtext(element=element,
                                   xpath=key, namespace=NAMESPACE)
        if name is None:
            name = volume['volumeId']
        svolume = StorageVolume(id=volume['volumeId'],
                                name=name,
                                size=int(volume['size']),
                                driver=self)
        try:
            created_time = datetime.strptime(volume['createTime'],
                                             '%Y-%m-%dT%H:%M:%S.%fZ')
        except ValueError:  # Wrong Format, try again..
            created_time = datetime.strptime(volume['createTime'],
                                             '%Y-%m-%dT%H:%M:%SZ')

        svolume.extra = {
            'createTime': created_time,
            'status': volume['status'],
            'attachmentSet': self._get_attachment_set(element_as)}
        return svolume

    def _getNextAvailableDevice(self, instance_id):
        """
        Given an instance_id
        return the next available location for attaching a volume
        relative to /dev/
        """
        def _attached_to_instance(vol):
            attached_instance_id = vol.extra.get(
                'attachmentSet', {}).get('instanceId', '')
            return attached_instance_id == instance_id

        # get all volumes that are attached to this instance
        # add devices to list
        attached_volumes = filter(_attached_to_instance, self.list_volumes())
        used_devices = [vol.extra.get('attachmentSet', {}).get('device')
                        for vol in attached_volumes]

        logger.debug('List of used devices:%s' % used_devices)

        # start with the letter b, increment until "xvd[char]"
        # is not in the list of used devices
        device_char_index = 1  # that's the index of b. /dev/xvda* is reserved
        letters = string.ascii_letters
        available_character = None
        while available_character is None:
            if '/dev/xvd' + letters[device_char_index] not in used_devices:
                available_character = letters[device_char_index]
            device_char_index = device_char_index + 1

        # Warning: this method will fail if you try to attach > 25 volumes
        # Probably not a typical use case, though
        return "/dev/xvd" + available_character

    def _to_volumes(self, element):
        element_volumes = findall(element=element,
                                  xpath='volumeSet/item', namespace=NAMESPACE)
        volumes = []
        for vol in element_volumes:
            volumes.append(self._to_volume(vol))
        return volumes

    def _to_nodes(self, object, xpath, groups=None, owner=None):
        return [self._to_node(el, groups=groups, owner=owner)
                for el in object.findall(fixxpath(xpath=xpath,
                                                  namespace=NAMESPACE))]

    def list_nodes(self, ex_node_ids=None):
        """
        Specific eucalyptus implementation to include 'owner' in the extra
        """
        params = {'Action': 'DescribeInstances'}
        if ex_node_ids:
            params.update(self._pathlist('InstanceId', ex_node_ids))
        elem = self.connection.request(self.path, params=params).object
        nodes = []
        for rs in findall(element=elem, xpath='reservationSet/item',
                          namespace=NAMESPACE):
            owner = findtext(element=rs, xpath='ownerId', namespace=NAMESPACE)
            groups = [g.findtext('')
                      for g in findall(element=rs,
                                       xpath='groupSet/item/groupId',
                                       namespace=NAMESPACE)]
            nodes += self._to_nodes(rs, 'instancesSet/item', groups, owner)

        nodes_elastic_ips_mappings = self.ex_describe_addresses(nodes)
        for node in nodes:
            ips = nodes_elastic_ips_mappings[node.id]
            node.public_ips.extend(ips)
        return nodes

    def list_volumes(self):
        """
        Eucalyptus specific implementation of list_volumes.
        """
        params = {'Action': 'DescribeVolumes'}
        element = self.connection.request(self.path, params).object
        volumes = self._to_volumes(element)
        return volumes

    def attach_volume(self, node, volume, device=None):
        if device is None:
            device = self._getNextAvailableDevice(node.id)
        result = super(Eucalyptus_Esh_NodeDriver, self).attach_volume(node,
                                                                    volume,
                                                                    device)
        logger.debug('Result of attaching device to %s:%s' % (device, result))
        return result

    def create_volume(self, size, name, location='bespin', *args, **kwargs):
        params = {'Action': 'CreateVolume',
                  'Size': str(size),
                  'AvailabilityZone': location, }
        volume_obj = self.connection.request(self.path, params=params).object
        volume = self._to_volume(volume_obj, name=name)
        logger.debug(volume)
        volume.extra.update({'name': name})
        return True, volume

    def list_sizes(self, location=None):
        """
        Eucalyptus 2 specific implementation of list_sizes.
        """
        params = {'Action': 'DescribeAvailabilityZones',
                  'ZoneName.1': 'verbose'}
        element = self.connection.request(self.path, params).object
        sizes = self._to_sizes(element)
        return sizes

    def _to_sizes(self, element):
        """
        Create a NodeSize object given a libcloud XML element.
        Extra information is available in nodesize.extra dictionary.
        """
        # elem_sizes = element/availabilityZoneInfo/item.
        # elem_sizes[0]  == zone and ip
        # elem_sizes[1]  == column descriptors
        # elem_sizes[2]+ == occupancy and type information.
        elem_sizes = findall(element=element,
                             xpath='availabilityZoneInfo/item',
                             namespace=NAMESPACE)[2:]
        sizes = []
        for s in elem_sizes:
            pieces = re.findall(r'\w+|!/', s[1].text)
            # expected format of pieces is
            # ['0058', '0215', '2', '4096', '10']
            # ['remaining', 'total', 'cpu', 'ram', 'disk']
            id = s[0].text.split()[1]
            size_info = {'id': id,
                         'name': id,
                         'ram': int(pieces[3]),
                         'disk': int(pieces[4]),
                         'bandwidth': 0,
                         'price': 0}
            node_size = NodeSize(driver=self, **size_info)
            node_size.extra = {'cpu': int(pieces[2]),
                               'occupancy': {'remaining': int(pieces[0]),
                                             'total': int(pieces[1])}}
            sizes.append(node_size)
        return sizes
