import inspect

import enum

from django.utils.module_loading import import_string
from django.core.exceptions import ImproperlyConfigured
from django.conf import settings
from threepio import logger


def load_plugin_class(plugin_path):
    return import_string(plugin_path)


class PluginManager(object):
    plugin_required = False
    plugin_required_message = "A Plugin is required."

    @classmethod
    def load_plugin(cls, plugin_path):
        """
        Use this method to load your plugins,
        usually based on a list of strings in
        the local.py settings file.
        """
        if cls.plugin_required and not plugin_path:
            raise ImproperlyConfigured(
                    cls.plugin_required_message)

        plugin = load_plugin_class(plugin_path)
        if cls.plugin_required and not plugin:
            raise ImproperlyConfigured(
                    cls.plugin_required_message)
        return plugin


class MachineValidationPluginManager(PluginManager):
    """
    Provide a plugin to create more complicated rules for default quotas
    """
    plugin_class_setting = getattr(settings, 'MACHINE_VALIDATION_PLUGIN', None)
    plugin_required = True
    plugin_required_message = """No Machine validation plugin has been defined.
To restore 'basic' functionality, please set settings.MACHINE_VALIDATION_PLUGIN to:
"atmosphere.plugins.machine_validation.BasicValidation"
"""

    @classmethod
    def get_validator(cls, account_driver, classpath=None):
        """
        Load MachineValidation plugin
        """
        if not classpath:
            classpath = cls.plugin_class_setting
        MachineValidationPluginCls = cls.load_plugin(classpath)
        try:
            machine_validator = MachineValidationPluginCls(account_driver)
        except:
            logger.exception(
                "Failed to initialize MachineValidation plugin %s"
                % MachineValidationPluginCls)
            raise
        return machine_validator


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


class DefaultQuotaPluginManager(PluginListManager):
    """
    Provide a plugin to create more complicated rules for default quotas
    """
    list_of_classes = getattr(settings, 'DEFAULT_QUOTA_PLUGINS', [])
    plugin_required = False

    @classmethod
    def default_quota(cls, user, provider):
        """
        Load each Default Quota Plugin and call `plugin.get_default_quota(user, provider)`
        """
        _default_quota = None
        for DefaultQuotaPlugin in cls.load_plugins(cls.list_of_classes):
            plugin = DefaultQuotaPlugin()
            try:
                inspect.getcallargs(
                    getattr(plugin, 'get_default_quota'),
                    user=user, provider=provider)
            except AttributeError:
                logger.info(
                    "Validation plugin %s missing method 'get_default_quota'"
                    % DefaultQuotaPlugin)
            except TypeError:
                logger.info(
                    "Validation plugin %s does not accept kwargs `user` & `provider`"
                    % DefaultQuotaPlugin)
            _default_quota = plugin.get_default_quota(user=user, provider=provider)
            if _default_quota:
                return _default_quota
        return _default_quota


@enum.unique
class EnforcementOverrideChoice(str, enum.Enum):
    ALWAYS_ENFORCE = 'ALWAYS_ENFORCE'
    NEVER_ENFORCE = 'NEVER_ENFORCE'
    NO_OVERRIDE = 'NO_OVERRIDE'


class AllocationSourcePluginManager(PluginListManager):
    """
    Provide a plugin to create more complicated rules for default quotas
    """
    list_of_classes = getattr(settings, 'ALLOCATION_SOURCE_PLUGINS', [])
    plugin_required = True  # For now...

    @classmethod
    def ensure_user_allocation_sources(cls, user, provider=None):
        """Load each Allocation Source Plugin and call `plugin.ensure_user_allocation_source(user)`

        Depending on the plugin this may create allocation sources if they don't already exist.
        :param user: The user to check
        :type user: core.models.AtmosphereUser
        :param provider: The provider (optional, not used by all plugins)
        :type provider: core.models.Provider
        :return: Whether the user has valid allocation sources
        :rtype: bool
        """
        _has_valid_allocation_sources = False
        for AllocationSourcePlugin in cls.load_plugins(cls.list_of_classes):
            plugin = AllocationSourcePlugin()
            try:
                inspect.getcallargs(
                    getattr(plugin, 'ensure_user_allocation_source'),
                    user=user, provider=provider)
            except AttributeError:
                logger.info(
                    "Allocation Source plugin %s missing method 'ensure_user_allocation_source'",
                    AllocationSourcePlugin)
            except TypeError:
                logger.info(
                    "Allocation Source plugin %s does not accept kwargs `user` & `provider`",
                    AllocationSourcePlugin)
            _has_valid_allocation_sources = plugin.ensure_user_allocation_source(user=user, provider=provider)
            if _has_valid_allocation_sources:
                return _has_valid_allocation_sources
        return _has_valid_allocation_sources

    @classmethod
    def get_enforcement_override(cls, user, allocation_source, provider=None):
        """Returns whether (and how) to override the enforcement for a particular user, allocation source and provider
        combination.

        Load each Allocation Source Plugin and call `plugin.get_enforcement_override(allocation_source)`. Will
        return the first value that is not `EnforcementOverrideChoice.NO_OVERRIDE`

        :param user: The user to check
        :type user: core.models.AtmosphereUser
        :param allocation_source: The allocation source to check
        :type allocation_source: core.models.AllocationSource
        :param provider: The provider (optional, not used by any plugins yet)
        :type provider: core.models.Provider
        :return: The enforcement override behaviour for the allocation source on the provider
        :rtype: EnforcementOverrideChoice
        """
        _enforcement_override_choice = EnforcementOverrideChoice.NO_OVERRIDE
        for AllocationSourcePlugin in cls.load_plugins(cls.list_of_classes):
            plugin = AllocationSourcePlugin()
            try:
                inspect.getcallargs(
                    getattr(plugin, 'get_enforcement_override'),
                    user=user, allocation_source=allocation_source, provider=provider)
            except AttributeError:
                logger.info(
                    "Allocation Source plugin %s missing method 'get_enforcement_override'",
                    AllocationSourcePlugin)
            except TypeError:
                logger.info(
                    "Allocation Source plugin %s does not accept kwargs `user`, `allocation_source`, & `provider`",
                    AllocationSourcePlugin)
            _enforcement_override_choice = plugin.get_enforcement_override(user=user,
                                                                           allocation_source=allocation_source,
                                                                           provider=provider)
            if _enforcement_override_choice != EnforcementOverrideChoice.NO_OVERRIDE:
                return _enforcement_override_choice
        return _enforcement_override_choice


class AccountCreationPluginManager(PluginListManager):
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
    successfully but has been deemed "Expired" by an external service.
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
            try:
                # TODO: Set a reasonable timeout but don't let it hold this indefinitely
                _is_expired = plugin.is_expired(user=user)
            except Exception as exc:
                logger.info("Expiration plugin %s encountered an error: %s" % (ExpirationPlugin, exc))
                _is_expired = True

            if _is_expired:
                return True
        return _is_expired
