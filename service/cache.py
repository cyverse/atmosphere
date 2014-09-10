import pickle  #  cPickle as pickle
from django.conf import settings
from django.utils import timezone

import redis

from threepio import logger

from api import get_esh_driver

from service.driver import get_admin_driver

admin_drivers = {}
drivers = {}


def _get_cached_admin_driver(provider, force=False):
    if not admin_drivers.get(provider) or force:
        admin_drivers[provider] = get_admin_driver(provider)
    return admin_drivers[provider]


def _get_cached_driver(provider=None, identity=None, force=False):
    if provider:
        return _get_cached_admin_driver(provider, force)
    if not drivers.get(identity) or force:
        drivers[identity] = get_esh_driver(identity)
    return drivers[identity]


def _get_cached(key, data_method, scrub_method, force=False):
    r = redis.StrictRedis()
    if force:
        r.delete(key)
    data = r.get(key)
    if not data:
        data = data_method()
        scrub_method(data)
        logger.debug("Updated redis({0}) using {1} and {2}".format(key, data_method, scrub_method))
        r.set(key, pickle.dumps(data))
        r.expire(key, 30)
        return data
    logger.debug("Actual type {0}".format(type(data)))
    return pickle.loads(data)


def _scrub(objects):
    for o in objects:
        o._connection = None
        for a in ["_node", "_volume", "_image"]:
            if hasattr(o, a):
                o.__dict__[a] = None
        if hasattr(o, "size") and hasattr(o.size, "_size"):
            if o.size._size:
                o.size._size = None


def _validate_parameters(provider, identity):
    if provider and identity:
        raise Exception("Use either provider or identity but not both.")


def get_cached_driver(provider=None, identity=None, force=False):
    _validate_parameters(provider, identity)
    return _get_cached_driver(provider=provider,
                              identity=identity,
                              force=force)


def get_cached_instances(provider=None, identity=None, force=False):
    _validate_parameters(provider, identity)
    cached_driver = _get_cached_driver(provider=provider, identity=identity,
                                       force=force)
    all_instances_method = cached_driver.list_all_instances
    if provider:
        key = "instances.{0}".format(provider.id)
    else:
        key = "instances.{0}.{1}".format(identity.created_by.username, identity.id)
    return _get_cached(key,
                       all_instances_method,
                       _scrub,
                       force=force)


def get_cached_volumes(provider=None, identity=None, force=False):
    _validate_parameters(provider, identity)
    cached_driver = _get_cached_driver(provider=provider, identity=identity,
                                       force=force)
    all_volumes_method = cached_driver.list_all_volumes
    if provider:
        key = "volumes.{0}".format(provider.id)
    else:
        key = "volumes.{0}.{1}".format(identity.created_by.username, identity.id)
    return _get_cached(key,
                       all_volumes_method,
                       _scrub,
                       force=force)


def get_cached_machines(provider=None, identity=None, force=False):
    _validate_parameters(provider, identity)
    cached_driver = _get_cached_driver(provider=provider, identity=identity,
                                       force=force)
    all_machines_method = cached_driver.list_machines
    if provider:
        key = "machines.{0}".format(provider.id)
    else:
        key = "machines.{0}.{1}".format(identity.created_by.username, identity.id)
    return _get_cached(key,
                       all_machines_method,
                       _scrub,
                       force=force)
