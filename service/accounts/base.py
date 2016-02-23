"""
Methods to cache data.
"""
import cPickle as pickle
import redis
# TODO: Make this look like a global (ALL_CAPS?)
# NOTE: This variable represents the globally-shared connection
redis_connection = None


class BaseAccountDriver(object):
    """
    Basic account driver -- Use this when your account driver can not be cached.
    """
    namespace = None

    def __init__(self, namespace="Atmosphere"):
        self.namespace = namespace

    def _get_image(self, *args, **kwargs):
        raise NotImplementedError("Implement this in the sub-class")

    def _list_all_images(self, *args, **kwargs):
        raise NotImplementedError("Implement this in the sub-class")

    def list_images(self, force=False, *args, **kwargs):
        """
        """
        return self._list_all_images(*args, **kwargs)

    def get_image(self, identifier, force=False, *get_method_args, **get_method_kwargs):
        return self._get_image(
                identifier,
                *get_method_args,
                **get_method_kwargs)


class CachedAccountDriver(object):
    """
    Basic account driver with caching
    -- Use this when your account driver can be cached.
    """
    cache_driver = None
    namespace = None

    def __init__(self, namespace="Atmosphere"):
        self.namespace = namespace
        self.cache_driver = CacheDriver(self.namespace)

    def _get_image(self, *args, **kwargs):
        raise NotImplementedError("Implement this in the sub-class")

    def _list_all_images(self, *args, **kwargs):
        raise NotImplementedError("Implement this in the sub-class")

    def list_images(self, force=False, *args, **kwargs):
        """
        """
        list_namespace = self.namespace + "_images"
        get_namespace = self.namespace + "_image"
        return self.cache_driver.cache_resource_list(
            list_namespace,
            self._list_all_images,
            resource_prefix=get_namespace,
            force=force,
            **kwargs)

    def get_image(self, identifier, force=False, *args, **kwargs):
        get_namespace = self.namespace + "_image_" + identifier
        return self.cache_driver.cache_resource(
            identifier,
            get_namespace,
            self._get_image,
            force=force,
            *args,
            **kwargs)


class CacheDriver():

    def __init__(self, namespace, timeout_sec=2 * 60):
        self.namespace = namespace
        self.timeout_sec = timeout_sec
        self.build_redis_connection()

    def build_redis_connection(self):
        global redis_connection
        if not redis_connection:
            redis_connection = redis.StrictRedis()

    def cache_resource(
            self,
            identifier,
            keyname,
            get_method,
            force=False,
            *get_method_args,
            **get_method_kwargs):
        """
        ReCache resources on first call/cache miss/force=True
        Returned cached resources whenever possible.
        If 'resource_prefix' is set:
            set individual resources in the list.
        """
        resource = None  # self.get_object(keyname)
        if not resource or force:
            resource = get_method(
                identifier,
                *get_method_args,
                **get_method_kwargs)
            self.set_object(keyname, resource)
        return resource

    def cache_resource_list(
            self,
            list_namespace,
            list_method,
            resource_prefix=None,
            resource_attr='id',
            force=False,
            **list_method_kwargs):
        """
        ReCache resources on first call/cache miss/force=True
        Returned cached resources whenever possible.
        If 'resource_prefix' is set:
            set individual resources in the list.
        """
        resources = None  # self.get_object(list_namespace)
        if not resources or force:
            resources = list_method(**list_method_kwargs)
            # Also set every individual resource in cache
            if resource_prefix:
                for resource in resources:
                    self.set_object(
                        "%s_%s" %
                        (resource_prefix,
                         getattr(
                             resource,
                             resource_attr)),
                        resource)
            self.set_object(list_namespace, resources)
        return resources

    def _get(self, name):
        return redis_connection.get(name)

    def get_object(self, name):
        value = self._get(name)
        return pickle.loads(value) if value else None

    def _set(self, name, value, timeout=None):
        if not timeout:
            timeout = self.timeout_sec
        redis_connection.set(name, value, ex=timeout)

    def set_object(self, name, value, timeout=None):
        if not timeout:
            timeout = self.timeout_sec
        self._set(name, pickle.dumps(value), timeout=timeout)
