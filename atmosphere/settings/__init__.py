"""
Settings for atmosphere project.

"""

from __future__ import absolute_import
from datetime import timedelta
from celery.schedules import crontab
from uuid import UUID
import logging
import os
import os.path
import sys

import threepio
import caslib

import atmosphere

#Debug Mode
DEBUG = True
TEMPLATE_DEBUG = DEBUG

SETTINGS_ROOT = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                            '../..'))
APPEND_SLASH = False
SERVER_URL = 'https://MYHOSTNAMEHERE'
# IF on the root directory, this should be BLANK, else: /path/to/web (NO
# TRAILING /)
REDIRECT_URL = ''

# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/1.5/ref/settings/#allowed-hosts
ALLOWED_HOSTS = [unicode(SERVER_URL.replace('https://', ''))]

#NOTE: first admin will be sender of atmo emails.
ADMINS = (
    ('Atmosphere Admin', 'atmo@iplantcollaborative.org'),
    ('J. Matt Peterson', 'jmatt@iplantcollaborative.org'),
    ('Steven Gregory', 'esteve@iplantcollaborative.org'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'NAME': 'atmosphere',
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'USER': 'atmo_app',
        'PASSWORD': 'atmosphere',
        'HOST': 'localhost',
        'PORT': '5432'
    },
}
INSTALLED_APPS = (
    #contrib apps
    'django.contrib.auth',
    'django.contrib.admin',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.staticfiles',

    #3rd party apps
    'rest_framework',
    'rest_framework_swagger',

    'south',
    'djcelery',
    'django_jenkins',
    'pipeline',
    'corsheaders',

    #iPlant apps
    'rtwo',

    #atmosphere apps
    'authentication',
    'service',
    'web',
    'core',
)

DATABASE_ROUTERS = ['atmosphere.routers.Service']

TIME_ZONE = 'America/Phoenix'

LANGUAGE_CODE = 'en-us'

SITE_ID = 1

USE_I18N = True

USE_TZ = True

# Absolute path to the directory that holds media.
# Example: '/home/media/media.lawrence.com/'
MEDIA_ROOT = os.path.join(PROJECT_ROOT, 'resources/')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: 'http://media.lawrence.com', 'http://example.com/media/'
MEDIA_URL = '/resources/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: 'http://foo.com/media/', '/media/'.
STATIC_ROOT = os.path.join(PROJECT_ROOT, 'static/')

STATIC_URL = '/static/'

STATICFILES_DIRS = (
    os.path.join(PROJECT_ROOT, "resources"),
)

# Make this unique, and don't share it with anybody.
# NOTE: This value is not used, check local.py!
SECRET_KEY = None

# This key however should stay the same, and be shared with all Atmosphere
ATMOSPHERE_NAMESPACE_UUID=UUID("40227dff-dedf-469c-a9f8-1953a7372ac1")

#django-pipeline configuration
PIPELINE = False

PIPELINE_ENABLED = False

STATICFILES_STORAGE = 'pipeline.storage.PipelineStorage'

PIPELINE_CSS = {
    'app': {
        'source_filenames': (
            'css/cloudfront.css',
        ),
        'output_filename': 'css/app.css',
        'extra_context': {
            'media': 'screen,projection',
        },
    },
}

PIPELINE_JS = {
    'app': {
        'source_filenames': (
            'js/cloudfront2.js',
            'js/base.js',
            'partials/templates.js',
        ),
        'output_filename': 'js/app.js',
    }
}

# List of callables that know how to import templates from various sources.
STATICFILES_FINDERS = (
    'pipeline.finders.FileSystemFinder',
    'pipeline.finders.AppDirectoriesFinder',
    'pipeline.finders.PipelineFinder',
    'pipeline.finders.CachedFileFinder',
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'pipeline.finders.AppDirectoriesFinder',
#    'pipeline.finders.CachedFileFinder',
)
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader'
)

MIDDLEWARE_CLASSES = (
    'corsheaders.middleware.CorsMiddleware',
    # corsheaders.middleware.CorsMiddleware Must be ahead of
    # configuration CommonMiddleware for an edge case.
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.middleware.gzip.GZipMiddleware',
    'pipeline.middleware.MinifyHTMLMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'atmosphere.slash_middleware.RemoveSlashMiddleware',
)

ROOT_URLCONF = 'atmosphere.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'atmosphere.wsgi.application'

TEMPLATE_DIRS = (
    os.path.join(PROJECT_ROOT, 'templates'),
)

AUTH_USER_MODEL = 'core.AtmosphereUser'
AUTH_USER_MODULE = 'core.AtmosphereUser'
AUTH_PROFILE_MODULE = 'core.UserProfile'

AUTHENTICATION_BACKENDS = (
    #'authentication.authBackends.CASLoginBackend',  # For Web-Access
    'authentication.authBackends.SAMLLoginBackend',  # For Web-Access
    'authentication.authBackends.LDAPLoginBackend',  # For Service-Access
    'authentication.authBackends.OAuthLoginBackend',  # For 3rd-party-web Service-Access
)

# django-cors-headers
CORS_ORIGIN_ALLOW_ALL = True
CORS_ORIGIN_WHITELIST = None

JENKINS_TASKS = (
    'django_jenkins.tasks.with_coverage',
    'django_jenkins.tasks.run_pep8',
    'django_jenkins.tasks.run_pyflakes',
)
# The age of session cookies, in seconds.
# http://docs.djangoproject.com/en/dev/ref/settings/
# http://docs.djangoproject.com/en/dev/topics/http/sessions/
# Now I set sessio cookies life time = 3600 seconds = 1 hour
#SESSION_COOKIE_AGE = 3600
SESSION_EXPIRE_AT_BROWSER_CLOSE = True


## ATMOSPHERE APP CONFIGS
# INSTANCE_SERVICE_URL = SERVER_URL + REDIRECT_URL+'/instanceservice/'
INSTANCE_SERVICE_URL = SERVER_URL + REDIRECT_URL + '/api/notification/'
API_SERVER_URL = SERVER_URL + REDIRECT_URL + '/resources/v1'
AUTH_SERVER_URL = SERVER_URL + REDIRECT_URL + '/auth'
INIT_SCRIPT_PREFIX = '/init_files/'
DEPLOY_SERVER_URL = SERVER_URL.replace("https", "http")

## logging
LOGGING_LEVEL = logging.DEBUG
DEP_LOGGING_LEVEL = logging.INFO  # Logging level for dependencies.
LOG_FILENAME = os.path.abspath(os.path.join(
    os.path.dirname(atmosphere.__file__),
    '..',
    'logs/atmosphere.log'))

threepio.initialize("atmosphere",
                    log_filename=LOG_FILENAME,
                    app_logging_level=LOGGING_LEVEL,
                    dep_logging_level=DEP_LOGGING_LEVEL)
## NOTE: The format for status_logger
# timestamp, user, instance_alias, machine_alias, size_alias, status_update

STATUS_LOG_FILENAME = os.path.abspath(os.path.join(
    os.path.dirname(atmosphere.__file__),
    '..',
    'logs/atmosphere_status.log'))
fh = logging.FileHandler(STATUS_LOG_FILENAME)
# create formatter and add it to the handlers
base_format = '%(message)s'
formatter = logging.Formatter(base_format)
fh.setFormatter(formatter)
threepio.status_logger = threepio\
        .initialize("atmosphere_status",
                    handlers=[fh],
                    app_logging_level=LOGGING_LEVEL,
                    dep_logging_level=DEP_LOGGING_LEVEL,
                    global_logger=False,
                    format=base_format)
threepio.email_logger = threepio\
        .initialize("atmosphere_email",
                    log_filename=LOG_FILENAME,
                    app_logging_level=LOGGING_LEVEL,
                    dep_logging_level=DEP_LOGGING_LEVEL,
                    global_logger=False)
threepio.api_logger = threepio\
        .initialize("atmosphere_api",
                    log_filename=LOG_FILENAME,
                    app_logging_level=LOGGING_LEVEL,
                    dep_logging_level=DEP_LOGGING_LEVEL,
                    global_logger=False)

##Directory that the app (One level above this file) exists
# (TEST if this is necessary)
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if 'PYTHONPATH' in os.environ:
    os.environ['PYTHONPATH'] = root_dir + ':' + os.environ['PYTHONPATH']
else:
    os.environ['PYTHONPATH'] = root_dir


## Redirect stdout to stderr.
sys.stdout = sys.stderr

##REST FRAMEWORK
REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': (
        # Included Renderers
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.JSONPRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
        'rest_framework.renderers.YAMLRenderer',
        'rest_framework.renderers.XMLRenderer',
        # Our Renderers
        'api.renderers.PNGRenderer',
        'api.renderers.JPEGRenderer',
    ),
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'authentication.token.OAuthTokenAuthentication',
        'authentication.token.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',

    )
}
#REST_FRAMEWORK_SWAGGER
SWAGGER_SETTINGS = {
    "exclude_namespaces": [
        "private_root_urls",
        "private_apis",
    ], # List URL namespaces to ignore
    "api_version": '0.1',  # Specify your API's version
    "api_path": "/",  # Specify the path to your API not a root level
    "enabled_methods": [  # Specify which methods to enable in Swagger UI
        'get',
        'post',
        'patch',
        'delete'
    ],
    "api_key": '', # An API key
    "is_authenticated": False,  # Set to True to enforce user authentication,
    "is_superuser": False,  # Set to True to enforce admin only access
}

##CASLIB
SERVER_URL = SERVER_URL + REDIRECT_URL
CAS_SERVER = 'https://auth.iplantcollaborative.org'
SERVICE_URL = SERVER_URL + '/CAS_serviceValidater?sendback='\
    + REDIRECT_URL + '/application/'
PROXY_URL = SERVER_URL + '/CAS_proxyUrl'
PROXY_CALLBACK_URL = SERVER_URL + '/CAS_proxyCallback'


#pyes secrets
ELASTICSEARCH_HOST = SERVER_URL
ELASTICSEARCH_PORT = 9200

#Django-Celery secrets
BROKER_URL = 'redis://localhost:6379/0'
BROKER_BACKEND = "redis"
REDIS_PORT = 6379
REDIS_HOST = "localhost"
BROKER_USER = ""
BROKER_PASSWORD = ""
REDIS_DB = 0
REDIS_CONNECT_RETRY = True
CELERY_ENABLE_UTC = True
CELERY_TIMEZONE = "America/Phoenix"
CELERY_SEND_EVENTS = True
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_TASK_RESULT_EXPIRES = 3*60*60 #Store results for 3 hours
#CELERYBEAT_SCHEDULER = "djcelery.schedulers.DatabaseScheduler"
CELERYBEAT_CHDIR=PROJECT_ROOT
CELERYD_MAX_TASKS_PER_CHILD=50
CELERYD_LOG_FORMAT="[%(asctime)s: %(name)s-%(levelname)s/%(processName)s [PID:%(process)d] @ %(pathname)s on %(lineno)d] %(message)s"
CELERYD_TASK_LOG_FORMAT="[%(asctime)s: %(name)s-%(levelname)s/%(processName)s [PID:%(process)d] [%(task_name)s(%(task_id)s)] @ %(pathname)s on %(lineno)d] %(message)s"

# Django-Celery Local Settings
#CELERY_QUEUES = (
#        Queue('imaging'), Exchange('imaging'), routing_key='imaging'),
#    )
CELERY_DEFAULT_QUEUE='default'

#NOTE: Leave this block out until the 'bug' regarding CELERY_ROUTES is fixed
#      See steve gregory for more details..

#     #NOTE: This is a Tuple of dicts!
#     from kombu import Queue
#     CELERY_QUEUES = (
#             Queue('default'),
#             Queue('imaging', routing_key='imaging.#')
#         )
CELERYBEAT_SCHEDULE = {
    "check_image_membership": {
        "task": "check_image_membership",
        "schedule": timedelta(minutes=15),
        "options": {"expires": 10*60, "time_limit":2*60,
                    "queue": "celery_periodic"}
    },
    "monitor_instances": {
        "task": "monitor_instances",
        "schedule" : timedelta(minutes=15),
        "options": {"expires":10*60, "time_limit":10*60,
                    "queue":"celery_periodic"}
    },
    "clear_empty_ips": {
        "task": "clear_empty_ips",
        "schedule": timedelta(minutes=20),
        "options":{"expires": 60*60,
                   "queue":"celery_periodic"}
    },
    "remove_empty_networks": {
        "task": "remove_empty_networks",
        "schedule": crontab(hour="*/2", minute="0", day_of_week="*"),
        "options": {"expires":5*60, "time_limit":5*60,
                    "queue": "celery_periodic"}
    },
}
CELERY_ROUTES= ('atmosphere.route_logger.RouteLogger', )
CELERY_ROUTES += ({
    "chromogenic.tasks.migrate_instance_task" : \
        {"queue": "imaging", "routing_key": "imaging.execute"},
    "chromogenic.tasks.machine_imaging_task" : \
        {"queue": "imaging", "routing_key": "imaging.execute"},
    "service.tasks.machine.freeze_instance_task" : \
        {"queue": "imaging", "routing_key": "imaging.prepare"},
    "service.tasks.machine.process_request" : \
        {"queue": "imaging", "routing_key": "imaging.complete"},
        },)
#     # Django-Celery Development settings
# CELERY_ALWAYS_EAGER = True
# CELERY_EAGER_PROPAGATES_EXCEPTIONS = True  # Issue #75

import djcelery
djcelery.setup_loader()


"""
Import local settings specific to the server, and secrets not checked into Git.
"""
from atmosphere.settings.local import *

"""
Mostly good for TEST settings, especially DB conf.
"""
if DEBUG:
    # Its OK if there is no testing.py on the server!
    try:
        from atmosphere.settings.testing import *
    except ImportError:
        pass
