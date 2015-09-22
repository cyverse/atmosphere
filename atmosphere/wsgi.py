"""
WSGI config for atmosphere project.

This module contains the WSGI application used by Django's development server
and any production WSGI deployments. It should expose a module-level variable
named ``application``. Django's ``runserver`` and ``runfcgi`` commands discover
this application via the ``WSGI_APPLICATION`` setting.

Usually you will have the standard Django WSGI application here, but it also
might make sense to replace the whole Django WSGI application with a custom one
that later delegates to the Django one. For example, you could introduce WSGI
middleware here, or combine a Django application with an application of another
framework.

"""
import os
import sys

# Adds the directory above wsgi.py to system path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, '/opt/env/atmo/lib/python2.7/site-packages/')
sys.path.insert(1, root_dir)

os.environ["DJANGO_SETTINGS_MODULE"] = "atmosphere.settings"

# NOTE: DO NOT MOVE ABOVE THIS LINE! Django will fail to import settings without knowing
# what settings module ('atmosphere.settings') to use!
# Failure to do so will result in 500 error, exception output in the
# apache logs.
from django.conf import settings
from threepio import logger

if hasattr(settings, "NEW_RELIC_ENVIRONMENT"):
    try:
        import newrelic.agent
        newrelic.agent.initialize(
            os.path.join(root_dir, "extras/newrelic/atmosphere_newrelic.ini"),
            settings.NEW_RELIC_ENVIRONMENT)
        logger.info("[A]Plugin: New Relic initialized!")
    except ImportError as bad_import:
        logger.warn("[A]Warning: newrelic not installed..")
        logger.warn(bad_import)
    except Exception as bad_config:
        logger.warn("[A]Warning: newrelic not initialized..")
        logger.warn(bad_config)
else:
    logger.info("[A]Plugin: Skipping New Relic setup. NEW_RELIC_ENVIRONMENT not defined in local.py")

#    root_dir,
#    'logs/libcloud.log'))

# This application object is used by any WSGI server configured to use this
# file. This includes Django's development server, if the WSGI_APPLICATION
# setting points here.
from django.core.wsgi import get_wsgi_application
try:
    application = get_wsgi_application()
except Exception as e:
    raise
