"""
Methods to cache data.
"""


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

    def get_image(
        self, identifier, force=False, *get_method_args, **get_method_kwargs
    ):
        return self._get_image(
            identifier, *get_method_args, **get_method_kwargs
        )
