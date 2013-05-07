"""
Extension of libcloud's Eucalyptus Node Driver.
"""
import re, copy, string
import base64, hmac, time
from datetime import datetime

from hashlib import sha256

from libcloud.utils.xml import findall, findtext, findattr
from libcloud.compute.base import NodeSize, StorageVolume, NodeImage
from libcloud.compute.types import Provider
from libcloud.compute.drivers.ec2 import EC2NodeDriver, NAMESPACE

from libcloud.utils.py3 import urlencode
from libcloud.utils.py3 import urlquote, b

from threepio import logger

class Esh_EC2NodeDriver(EC2NodeDriver):
    """
    Amazon EC2 Node Driver
    """

    def _get_attachment_set(self, element):
        """
        TEST
        """
        attachment_set = {}
        for elem in element:
            for key in ['volumeId', 'instanceId', 'device', 'status', 'attachTime']:
                value = findtext(element=elem, xpath=key, namespace=NAMESPACE)
                if value:
                    attachment_set[key] = value
        if attachment_set.get('attachTime', None):
            if '.' in attachment_set['attachTime']:
                attach_date = datetime.strptime(attachment_set['attachTime'], '%Y-%m-%dT%H:%M:%S.%fZ')
            else:
                attach_date = datetime.strptime(attachment_set['attachTime'], '%Y-%m-%dT%H:%M:%SZ')
            attachment_set['attachTime'] = attach_date
        return attachment_set

    def _to_volumes(self, element):
        element_volumes = findall(element=element, xpath='volumeSet/item', namespace=NAMESPACE)
        return [self._to_volume(volume) for volume in element_volumes]

    def _to_volume(self, element, name=None):
        element_as = findall(element=element, xpath='attachmentSet/item', namespace=NAMESPACE)
        volume = {}
        for key in ['volumeId', 'size', 'createTime', 'status', 'attachmentSet']:
            volume[key] = findtext(element=element, xpath=key, namespace=NAMESPACE)
        if name is None:
            name = volume['volumeId']
        svolume = StorageVolume(id=volume['volumeId'],
                                name=name,
                                size=int(volume['size']),
                                driver=self)
        svolume.extra = {'createTime': datetime.strptime(volume['createTime'],
                                                         '%Y-%m-%dT%H:%M:%S.%fZ'),
                         'status': volume['status'],
                         'attachmentSet': self._get_attachment_set(element_as)}
        return svolume

    def list_volumes(self):
        """
        Eucalyptus specific implementation of list_volumes.
        """
        params = {'Action' : 'DescribeVolumes'}
        element = self.connection.request(self.path, params).object
        volumes = self._to_volumes(element)
        return volumes

    def _build_filter_query(self, query, filter_by):
        """
        Filter syntax found in EC2 API
            Filter.1.Name=owner-alias
            Filter.1.Value.1=amazon
            Filter.1.Value.2=aws-marketplace
            Filter.2.Name=image-type
            Filter.2.Value.1=machine
            ...
        """
        if type(filter_by) is not dict or type(query) is not dict:
            return None
        for (idx,(filter_name,filter_values)) in enumerate(filter_by.items()):
            #Add the new filter by name
            filter_str = 'Filter.%s.Name' % (idx+1)
            query[filter_str] = filter_name
            if type(filter_values) != list:
                filter_values = [filter_values]
            for value_idx, value in enumerate(filter_values):
                #Add each value found for the filter
                filter_str = 'Filter.%s.Value.%s' % (idx+1, value_idx+1)
                query[filter_str] = value
        return query

    def ex_filter_machines(self, filter_by={}):
        """
        Using filter_by:
        #Keys in the dict must match the EC2 API: See "Supported Filters" at http://goo.gl/XNOJv
        #Values in the dict must be str/[str,str,..]
        #EX:
        #Human Readable:
            All windows machines on AWS Marketplace or built by Amazon
        #filter_by=
            {'owner-alias':['amazon','aws-marketplace'], 'image-type':'machine', 'platform':'windows'}
        """
        query = {'Action': 'DescribeImages'}
        self._build_filter_query(query, filter_by)
        images = self._to_images(
            self.connection.request(self.path, query).object
        )
        return images
