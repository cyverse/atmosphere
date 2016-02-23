import cPickle as pickle
from django.conf import settings
from django.utils import timezone

import redis

from threepio import logger

from service.driver import get_esh_driver, get_admin_driver


admin_drivers = {}
drivers = {}
connection = None

INSTANCES_KEY_PROVIDER = "instances.{0}"
INSTANCES_KEY_IDENTITY = "instances.{0}.{1}"
VOLUMES_KEY_PROVIDER = "volumes.{0}"
VOLUMES_KEY_IDENTITY = "volumes.{0}.{1}"
MACHINES_KEY_PROVIDER = "machines.{0}"
MACHINES_KEY_IDENTITY = "machines.{0}.{1}"


def _get_cached_admin_driver(provider, force=True):
    if not admin_drivers.get(provider) or force:
        admin_drivers[provider] = get_admin_driver(provider)
    return admin_drivers[provider]


def _get_cached_driver(provider=None, identity=None, force=True):
    if provider:
        return _get_cached_admin_driver(provider, force)
    if not drivers.get(identity) or force:
        drivers[identity] = get_esh_driver(identity)
    return drivers[identity]


def redis_connection():
    global connection
    if not connection:
        connection = redis.StrictRedis()
    return connection


def _invalidate(key):
    r = redis_connection()
    if key:
        r.delete(key)


def _get_cached(key, data_method, scrub_method, force=False):
    try:
        r = redis_connection()
        if force:
            _invalidate(key)
        data = r.get(key)
    except redis.exceptions.ConnectionError:
        logger.error("EXTERNAL SERVICE redis-server IS NOT RUNNING! "
                     "Somebody should turn it on!")
        data = None
    if not data:
        data = data_method()
        scrub_method(data)
        logger.debug("Updated redis({0}) using {1} and {2}".format(
            key, data_method, scrub_method))
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


def get_cached_driver(provider=None, identity=None, force=True):
    _validate_parameters(provider, identity)
    return _get_cached_driver(provider=provider,
                              identity=identity,
                              force=force)


def get_cached_instances(provider=None, identity=None, force=False):
    _validate_parameters(provider, identity)
    cached_driver = _get_cached_driver(provider=provider, identity=identity,
                                       force=force)

    #NOTE: THIS IS A HACK -- The 'admin' user should be able to see "All the things" -- HOWEVER
    # In the current implementation of liberty on jetstream, a call to 'list_all_tenants'
    # Made by a user with a single tenant will produce *IDENTICAL* results to that same call made by admin.
    # THIS IS CONSIDERED HARMFUL! So we have blocked all users except the admin accounts from making this call.
    if identity and identity.created_by and identity.created_by.username in ['atmoadmin', 'admin']:
        instances_method = cached_driver.list_all_instances
    else:
        instances_method = cached_driver.list_instances

    if provider:
        key = INSTANCES_KEY_PROVIDER.format(provider.id)
    else:
        key = INSTANCES_KEY_IDENTITY.format(identity.created_by.username,
                                            identity.id)
    return _get_cached(key,
                       instances_method,
                       _scrub,
                       force=force)


def invalidate_cached_instances(provider=None, identity=None):
    if provider:
        key = INSTANCES_KEY_PROVIDER.format(provider.id)
    else:
        key = INSTANCES_KEY_IDENTITY.format(identity.created_by.username,
                                            identity.id)
    _invalidate(key)


def get_cached_volumes(provider=None, identity=None, force=False):
    _validate_parameters(provider, identity)
    cached_driver = _get_cached_driver(provider=provider, identity=identity,
                                       force=force)
    volumes_method = cached_driver.list_all_volumes
    if provider:
        key = VOLUMES_KEY_PROVIDER.format(provider.id)
    else:
        key = VOLUMES_KEY_IDENTITY.format(identity.created_by.username,
                                          identity.id)
    return _get_cached(key,
                       volumes_method,
                       _scrub,
                       force=force)


def invalidate_cached_volumes(provider=None, identity=None):
    if provider:
        key = VOLUMES_KEY_PROVIDER.format(provider.id)
    else:
        key = VOLUMES_KEY_IDENTITY.format(identity.created_by.username,
                                          identity.id)
    _invalidate(key)


def get_cached_machines(provider=None, identity=None, force=False):
    _validate_parameters(provider, identity)
    cached_driver = _get_cached_driver(provider=provider, identity=identity,
                                       force=force)
    machines_method = cached_driver.list_machines
    if provider:
        key = MACHINES_KEY_PROVIDER.format(provider.id)
    else:
        key = MACHINES_KEY_IDENTITY.format(identity.created_by.username,
                                           identity.id)
    return _get_cached(key,
                       machines_method,
                       _scrub,
                       force=force)


def invalidate_cached_machines(provider=None, identity=None):
    if provider:
        key = MACHINES_KEY_PROVIDER.format(provider.id)
    else:
        key = MACHINES_KEY_IDENTITY.format(identity.created_by.username,
                                           identity.id)
    _invalidate(key)
