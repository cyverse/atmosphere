import inspect

from django.utils.module_loading import import_string
from django.core.exceptions import ImproperlyConfigured
from django.conf import settings
from threepio import logger


def load_plugin_class(plugin_path):
    return import_string(plugin_path)


class PluginListManager(object):
    plugin_required = False
    plugin_required_message = "At least one plugin is required."

    @classmethod
    def load_plugins(cls, list_of_classes):
        """
        Use this method to load your plugins,
        usually based on a list of strings in
        the local.py settings file.
        """
        plugin_class_list = []
        for plugin_path in list_of_classes:
            fn = load_plugin_class(plugin_path)
            plugin_class_list.append(fn)
        if cls.plugin_required and not plugin_class_list:
            raise ImproperlyConfigured(
                    cls.plugin_required_message)
        return plugin_class_list


class AccountCreation(PluginListManager):
    """
    At least one plugin is required to create accounts for Atmosphere
    A sample account creation plugin has been provided for you:
    - atmosphere.plugins.accounts.creation.UserGroup

    This plugin will be responsible for taking the input (Username and a Provider)
    And expected to create: AtmosphereUser, Group, Credential+Identity (and associated dependencies, memberships)
    """
    list_of_classes = getattr(settings, 'ACCOUNT_CREATION_PLUGINS', [])
    plugin_required = True
    plugin_required_message = """No account creation backend has been defined.
To restore 'basic' functionality, please set settings.ACCOUNT_CREATION_PLUGINS to:
["atmosphere.plugins.accounts.creation.UserGroup",]"""


    @classmethod
    def create_accounts(cls, provider, username, force=False):
        accounts = []
        for AccountCreationPluginCls in cls.load_plugins(cls.list_of_classes):
            plugin = AccountCreationPluginCls()
            created = plugin.create_accounts(provider=provider, username=username, force=force)
            if created:
                accounts.extend(created)
        return accounts

    @classmethod
    def delete_accounts(cls, provider, username):
        """
        Load the accountsCreationPlugin and call `plugin.delete_accounts(provider, username)`
        """
        accounts = []
        for AccountCreationPluginCls in cls.load_plugins(cls.list_of_classes):
            plugin = AccountCreationPluginCls()
            deleted = plugin.delete_accounts(provider=provider, username=username)
            if deleted:
                accounts.extend(deleted)
        return accounts


class ValidationPluginManager(PluginListManager):
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


class ExpirationPluginManager(PluginListManager):
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
