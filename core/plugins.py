from django.utils.module_loading import import_string
from django.core.exceptions import ImproperlyConfigured

def load_plugin(plugin_path):
    return import_string(plugin_path)

def load_validation_plugins():
    from atmosphere import settings
    validation_classes = []
    available_plugins = [] \
        if not hasattr(settings, 'VALIDATION_PLUGINS') \
        else settings.VALIDATION_PLUGINS
    for validation_path in available_plugins:
        fn = load_plugin(validation_path)
        validation_classes.append(fn)
    if not validation_classes:
        raise ImproperlyConfigured(
            "No validation backend has been defined. "
            "If all users are considered valid, "
            "please set settings.VALIDATION_PLUGINS to: "
            "('atmosphere.plugins.auth.validation.AlwaysAllow',)")
    return validation_classes
