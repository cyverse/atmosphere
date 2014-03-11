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

#Adds the directory above wsgi.py to system path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, '/opt/env/atmo/lib/python2.7/site-packages/')
sys.path.insert(1, root_dir)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "atmosphere.settings")
#LIBCLOUD_DEBUG = os.path.abspath(os.path.join(
#    root_dir,
#    'logs/libcloud.log'))
#os.environ.setdefault("LIBCLOUD_DEBUG",LIBCLOUD_DEBUG)

# This application object is used by any WSGI server configured to use this
# file. This includes Django's development server, if the WSGI_APPLICATION
# setting points here.
from django.core.wsgi import get_wsgi_application
try:
    application = get_wsgi_application()
except Exception, e:
    e.msg = os.path.dirname(__file__)
    raise e

#from helloworld.wsgi import HelloWorldApplication
#application = HelloWorldApplication(application)
