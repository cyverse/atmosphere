"""
Common functions used by all Openstack managers 
"""
from keystoneclient.v3 import client as ks_client
from novaclient import client as nova_client
import glanceclient

def _connect_to_keystone(*args, **kwargs):
    """
    """
    keystone = ks_client.Client(*args, **kwargs)
    keystone.management_url = keystone.management_url.replace('v2.0','v3')
    keystone.version = 'v3'
    return keystone

def _connect_to_glance(keystone, version='1', *args, **kwargs):
    """
    NOTE: We use v1 because moving up to v2 results in a LOSS OF
    FUNCTIONALITY..
    """
    glance_endpoint = keystone.service_catalog.url_for(
                                            service_type='image',
                                            endpoint_type='publicURL')
    auth_token = keystone.service_catalog.get_token()
    glance = glanceclient.Client(version,
                          endpoint=glance_endpoint,
                          token=auth_token['id'])
    return glance

def _connect_to_nova(version='1.1', *args, **kwargs):
    region_name = kwargs.get('region_name'),
    nova = nova_client.Client(version,
                              kwargs.pop('username'),
                              kwargs.pop('password'),
                              kwargs.pop('tenant_name'),
                              kwargs.pop('auth_url'),
                              kwargs.pop('region_name'),
                              *args, no_cache=True, **kwargs)
    nova.client.region_name = region_name
    return nova

def findall(manager, *args, **kwargs):
    """
        Find all items with attributes matching ``**kwargs``.

        This isn't very efficient: it loads the entire list then filters on
        the Python side.
    """
    found = []
    searches = kwargs.items()

    for obj in manager.list():
        try:
            if all(getattr(obj, attr) == value
                   for (attr, value) in searches):
                found.append(obj)
        except AttributeError:
            continue

    return found

def find(manager, **kwargs):
        """
        Find a single item with attributes matching ``**kwargs``.

        This isn't very efficient: it loads the entire list then filters on
        the Python side.
        """
        rl = findall(manager, **kwargs)
        num = len(rl)

        if num == 0:
            msg = "No %s matching %s." % (manager.resource_class.__name__, kwargs)
            raise exceptions.NotFound(404, msg)
        elif num > 1:
            raise exceptions.NoUniqueMatch
        else:
            return rl[0]
