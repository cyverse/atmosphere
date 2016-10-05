import inspect

from django.utils.module_loading import import_string
from django.core.exceptions import ImproperlyConfigured
from django.conf import settings
from threepio import logger


def load_plugin_class(plugin_path):
    return import_string(plugin_path)


class PluginManager(object):
    plugin_required = False
    plugin_required_message = "At least one plugin is required."

    @classmethod
    def load_plugins(cls, list_of_classes):
        """
        Use this method to load your plugins,
        usually based on a list of strings in
        the local.py settings file.
        """
        plugin_classes = []
        for plugin_path in list_of_classes:
            fn = load_plugin_class(plugin_path)
            plugin_classes.append(fn)
        if cls.plugin_required and not plugin_classes:
            raise ImproperlyConfigured(
                    cls.plugin_required_message)
        return plugin_classes


class ValidationPluginManager(PluginManager):
    """
    At least one plugin is required to test user validation.
    A sample validation plugin has been provided for you:
    - atmosphere.plugins.auth.validation.AlwaysAllow

    If a user fails the validation plugin test
    they will not be able to access the Atmosphere API.
    """
    list_of_classes = getattr(settings, 'VALIDATION_PLUGINS', [])
    plugin_required = True
    plugin_required_message = """No validation backend has been defined.
If all users are considered valid,
please set settings.VALIDATION_PLUGINS to:
('atmosphere.plugins.auth.validation.AlwaysAllow',)"""

    @classmethod
    def is_valid(cls, user):
        """
        Load each ValidationPlugin and call `plugin.validate_user(user)`
        """
        _is_valid = False
        for ValidationPlugin in cls.load_plugins(cls.list_of_classes):
            plugin = ValidationPlugin()
            try:
                inspect.getcallargs(
                    getattr(plugin, 'validate_user'),
                    user=user)
            except AttributeError:
                logger.info(
                    "Validation plugin %s missing method 'validate_user'"
                    % ValidationPlugin)
            except TypeError:
                logger.info(
                    "Validation plugin %s does not accept kwarg `user`"
                    % ValidationPlugin)
            _is_valid = plugin.validate_user(user=user)
            if _is_valid:
                return True
        return _is_valid


class ExpirationPluginManager(PluginManager):
    """
    Plugins to test user expiration are not required.
    Use this if you wish to signal to Troposphere that a user has authenticated
    succesfully but has been deemed "Expired" by an external service.
    This will not directly stop the user from accessing the Atmosphere APIs.
    For that, see ValidationPlugin
    """
    list_of_classes = getattr(settings, 'EXPIRATION_PLUGINS', [])

    @classmethod
    def is_expired(cls, user):
        """
        Load each ExpirationPlugin and call `plugin.is_expired(user)`
        """
        _is_expired = False
        for ExpirationPlugin in cls.load_plugins(cls.list_of_classes):
            plugin = ExpirationPlugin()
            try:
                inspect.getcallargs(
                    getattr(plugin, 'is_expired'),
                    user=user)
            except AttributeError:
                logger.info(
                    "Expiration plugin %s does not have a 'is_expired' method"
                    % ExpirationPlugin)
            except TypeError:
                logger.info("Expiration plugin %s does not accept kwarg `user`"
                            % ExpirationPlugin)
            _is_expired = plugin.is_expired(user=user)
            if _is_expired:
                return True
        return _is_expired
