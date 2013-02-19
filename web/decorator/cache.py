"""
Cache for atmosphere.web
"""

from django.core.cache import cache as dcache

import atmosphere.settings as settings
from atmosphere.logger import logger

def cache_key(func, args, kwargs):
    """Creates a cache key using func"""
    module = "" if func.__module__ is None else str(func.__module__)
    fname = str(func.func_name)
    argnames = func.func_code.co_varnames[:func.func_code.co_argcount]
    key = str(module + fname + "(" + ", ".join(
            "%s=%r" % entry
            for entry in zip(argnames,args[:len(argnames)])+[("args",list(args[len(argnames):]))]+[("kwargs",kwargs)]) +")")
    return key

def cache(func):
    """Decorator. Caches the result of the function with django.core.cache
    get and set functions. They key is created using the cache_key function."""
    def cache_func(*args, **kwargs):
        result = None
        # cache if it's enabled.
        if settings.CACHES:
            key = cache_key(func, args, kwargs)
            logger.info("cache using key: %s" % key)
            result = dcache.get(key)
            if not result:
                logger.info("Cache not found/expired, Recaching..")
                result = func(*args, **kwargs)
                dcache.set(key, result)
        else:
            logger.info("nocache mode")
            result = func(*args, **kwargs)
        return result
    return cache_func
