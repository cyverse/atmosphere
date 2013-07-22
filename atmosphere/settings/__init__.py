# Settings for atmosphere project.

from __future__ import absolute_import
from datetime import timedelta
import logging
import os
import os.path
import sys

import threepio
import caslib

import atmosphere

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SERVER_URL = 'https://yourserver.iplantc.org'
# IF on the root directory, this should be BLANK, else: /path/to/web (NO
# TRAILING /)
REDIRECT_URL = ''

# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/1.5/ref/settings/#allowed-hosts
ALLOWED_HOSTS = [SERVER_URL.replace('https://', '')]

#NOTE: first admin will be sender of atmo emails.
ADMINS = (
    ('Atmosphere Admin', 'atmo@iplantcollaborative.org'),
    ('J. Matt Peterson', 'jmatt@iplantcollaborative.org'),
    ('Steven Gregory', 'esteve@iplantcollaborative.org'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'NAME': 'space_dev',
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'USER': 'atmo_app',
        'PASSWORD': 'atmosphere',
        'HOST': 'localhost',
        'PORT': '5432'
    },
}

DATABASE_ROUTERS = ['atmosphere.routers.Service']

TIME_ZONE = 'America/Phoenix'

LANGUAGE_CODE = 'en-us'

SITE_ID = 1

USE_I18N = True

USE_TZ = True

# Absolute path to the directory that holds media.
# Example: '/home/media/media.lawrence.com/'
MEDIA_ROOT = PROJECT_ROOT + '/resources/'

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: 'http://media.lawrence.com', 'http://example.com/media/'
MEDIA_URL = '/resources/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: 'http://foo.com/media/', '/media/'.
STATIC_ROOT = PROJECT_ROOT + '/static/'

STATIC_URL = '/static/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = '785nc+)g%w!g01#$#lc+weg2b!yc^z#17rvjln0c5r39*vg8%t'

# List of callables that know how to import templates from various sources.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder'
)
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader'
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'atmosphere.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'atmosphere.wsgi.application'

TEMPLATE_DIRS = (
    os.path.join(PROJECT_ROOT, 'templates'),
)

AUTH_PROFILE_MODULE = 'core.UserProfile'

AUTHENTICATION_BACKENDS = (
    'authentication.authBackends.CASLoginBackend',  # For Web-Access
    'authentication.authBackends.LDAPLoginBackend',  # For Service-Access
    #'django.contrib.auth.backends.ModelBackend',
)

INSTALLED_APPS = (
    #contrib apps
    'django.contrib.auth',
    'django.contrib.admin',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.staticfiles',

    #3rd party apps
    'rest_framework',
    'south',
    'djcelery',

    #iPlant apps
    'rtwo',

    #atmosphere apps
    'authentication',
    'service',
    'web',
    'core',
)

# The age of session cookies, in seconds.
# http://docs.djangoproject.com/en/dev/ref/settings/
# http://docs.djangoproject.com/en/dev/topics/http/sessions/#topics-http-sessions
# Now I set sessio cookies life time = 3600 seconds = 1 hour
#SESSION_COOKIE_AGE = 3600
SESSION_EXPIRE_AT_BROWSER_CLOSE = True


## ATMOSPHERE APP CONFIGS
# INSTANCE_SERVICE_URL = SERVER_URL + REDIRECT_URL+'/instanceservice/'
INSTANCE_SERVICE_URL = SERVER_URL + REDIRECT_URL + '/api/notification/'
API_SERVER_URL = SERVER_URL + REDIRECT_URL + '/resources/v1'
AUTH_SERVER_URL = SERVER_URL + REDIRECT_URL + '/auth'
INIT_SCRIPT_PREFIX = '/init_files/'


## logging
DEBUG = True
TEMPLATE_DEBUG = DEBUG
LOGGING_LEVEL = logging.DEBUG
DEP_LOGGING_LEVEL = logging.DEBUG  # Logging level for dependencies.
LOG_FILENAME = os.path.abspath(os.path.join(
    os.path.dirname(atmosphere.__file__),
    '..',
    'logs/atmosphere.log'))
threepio.initialize("atmosphere",
                    log_filename=LOG_FILENAME,
                    app_logging_level=LOGGING_LEVEL,
                    dep_logging_level=DEP_LOGGING_LEVEL)
threepio.email_logger = threepio.initialize("atmosphere_email",
                                            log_filename=LOG_FILENAME,
                                            app_logging_level=LOGGING_LEVEL,
                                            dep_logging_level=DEP_LOGGING_LEVEL,
                                            global_logger=False)

##Directory that the app (One level above this file) exists
# (TEST if this is necessary)
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if os.environ.has_key('PYTHONPATH'):
    os.environ['PYTHONPATH'] = root_dir + ':' + os.environ['PYTHONPATH']
else:
    os.environ['PYTHONPATH'] = root_dir


## Redirect stdout to stderr.
sys.stdout = sys.stderr

##REST FRAMEWORK
REST_FRAMEWORK = {
        'DEFAULT_RENDERER_CLASSES': (
                'rest_framework.renderers.JSONRenderer',
                'rest_framework.renderers.JSONPRenderer',
                'rest_framework.renderers.BrowsableAPIRenderer',
                'rest_framework.renderers.YAMLRenderer',
                'rest_framework.renderers.XMLRenderer',
        ),
        'DEFAULT_AUTHENTICATION_CLASSES': (
            'authentication.token.TokenAuthentication',
        )
}
##CASLIB
SERVER_URL = SERVER_URL + REDIRECT_URL
CAS_SERVER = 'https://auth.iplantcollaborative.org'
SERVICE_URL = SERVER_URL + '/CAS_serviceValidater?sendback=' + REDIRECT_URL + '/application/'
PROXY_URL = SERVER_URL + '/CAS_proxyUrl'
PROXY_CALLBACK_URL = SERVER_URL + '/CAS_proxyCallback'
caslib.cas_init(CAS_SERVER, SERVICE_URL, PROXY_URL, PROXY_CALLBACK_URL)

##CACHE SETTINGS
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'atmosphere_cache_requests',
        'TIMEOUT': 18000,
    }
}

###############
#   SECRETS   #
###############

# CLEAR ALL VALUES BELOW THIS LINE BEFORE PUSHING TO DIST

##ATMO SETTINGS
ATMOSPHERE_VNC_LICENSE = ""

##AUTH SETTINGS
TOKEN_EXPIRY_TIME = timedelta(days=1)
LDAP_SERVER = "ldap://ldap.iplantcollaborative.org"
LDAP_SERVER_DN = "ou=people,dc=iplantcollaborative,dc=org"

##SERVICE SETTINGS
#Eucalyptus provider secrets
EUCA_S3_URL = ""
EUCA_EC2_URL = ""
EUCA_ADMIN_KEY = ""
EUCA_ADMIN_SECRET = ""

#
# IMAGING SETTINGS
#

# LOCAL STORAGE
# Local storage is necessary for imaging Eucalyptus
# There should be a minimum of 10GB of space remaining
# before attempting imaging.
# Ideally, this location should point to a storage volume
LOCAL_STORAGE = '/tmp'

#Eucalyptus Imaging secrets
EUCA_PRIVATE_KEY = ""
EC2_CERT_PATH = ""
EUCALYPTUS_CERT_PATH = ""

#Eucalyptus Dicts
EUCA_IMAGING_ARGS = {
    'key': EUCA_ADMIN_KEY,
    'secret': EUCA_ADMIN_SECRET,
    'ec2_url': EUCA_EC2_URL,
    's3_url': EUCA_S3_URL,
    'ec2_cert_path': EC2_CERT_PATH,
    'pk_path': EUCA_PRIVATE_KEY,
    'euca_cert_path': EUCALYPTUS_CERT_PATH,
    'config_path': '/services/Configuration',
    'extras_root': PROJECT_ROOT
}
EUCALYPTUS_ARGS = {
    'key': EUCA_ADMIN_KEY,
    'secret': EUCA_ADMIN_SECRET,
    'url': EUCA_EC2_URL,
    'account_path': '/services/Accounts'
}

#Openstack provider secrets
OPENSTACK_ADMIN_KEY = ""
OPENSTACK_ADMIN_SECRET = ""
OPENSTACK_AUTH_URL = ''
OPENSTACK_ADMIN_URL = OPENSTACK_AUTH_URL.replace("5000", "35357")
OPENSTACK_ADMIN_TENANT = ""
OPENSTACK_DEFAULT_REGION = ""
OPENSTACK_DEFAULT_ROUTER = ""

OPENSTACK_ARGS = {
    'username': OPENSTACK_ADMIN_KEY,
    'password': OPENSTACK_ADMIN_SECRET,
    'tenant_name': OPENSTACK_ADMIN_TENANT,
    'auth_url': OPENSTACK_ADMIN_URL,
    'region_name': OPENSTACK_DEFAULT_REGION
}
OPENSTACK_NETWORK_ARGS = {
    'auth_url': OPENSTACK_ADMIN_URL,
    'region_name': OPENSTACK_DEFAULT_REGION,
    'router_name': OPENSTACK_DEFAULT_ROUTER
}

#AWS Provider secrets
AWS_KEY = ""
AWS_SECRET = ""
AWS_S3_URL = ""
AWS_S3_KEY = ""
AWS_S3_SECRET = ""

#pyes secrets
ELASTICSEARCH_HOST = SERVER_URL
ELASTICSEARCH_PORT = 9200

#Django-Celery secrets
BROKER_URL = ""
BROKER_BACKEND = "redis"
REDIS_PORT = 6379
REDIS_HOST = ""
BROKER_USER = ""
BROKER_PASSWORD = ""
REDIS_DB = 0
REDIS_CONNECT_RETRY = True
CELERY_SEND_EVENTS = True
CELERY_RESULT_BACKEND = 'redis'
CELERY_TASK_RESULT_EXPIRES = 10
CELERYBEAT_SCHEDULER = "djcelery.schedulers.DatabaseScheduler"
#Django-Celery Development settings
#CELERY_ALWAYS_EAGER = True

import djcelery
djcelery.setup_loader()

"""
Import local settings, specific to the server this code is running on.
Mostly good for TEST settings, especially DB conf.
"""
try:
    from settings.local import *
# Its OK if there is no local.py on the server!
except ImportError:
    pass
