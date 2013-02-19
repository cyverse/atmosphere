"""
Logging for dashboard website.

Provides two separate log levels. One for dependencies and one for the application.

django's settings.py:

  ## logging imports
  import logging
  import atmosphere.logger

  ## logging
  DEBUG = True
  TEMPLATE_DEBUG = DEBUG
  LOGGING_LEVEL = logging.DEBUG
  DEP_LOGGING_LEVEL = logging.WARN#Logging level for dependencies.
  atmosphere.logger.initialize(LOGGING_LEVEL, DEP_LOGGING_LEVEL)

example use:

  from atmosphere.logger import logger
  # ...
  logger.debug('debugorz')
  logger.info('infoz')

"""

from __future__ import absolute_import
import atmosphere
import logging
import os.path
import json

logger = None

email_logger = None

def logger_initialize(logger):
    """
    Customize the application logger.
    Examples of customization: Set formatter or change, add, remove handlers.
    """
    pass

def initialize(app_log_level, dep_log_level):
    """
    Initialize the root and application logger.
    """
    format = "%(asctime)s %(name)s-%(levelname)s [%(pathname)s %(lineno)d] %(message)s"
    formatter = logging.Formatter(format)
    log_file = os.path.abspath(os.path.join(
            os.path.dirname(atmosphere.__file__),
            '..',
            'logs/atmosphere.log'))

    # Setup the root logging for dependencies, etc.
    logging.basicConfig(
        level = dep_log_level,
        format = format,
        filename = log_file,
        filemode = 'a+')

    # Setup and add separate application logging.
    global logger, email_logger
    logger = logging.getLogger('atmosphere')
    logger_initialize(logger)
    logger.setLevel(app_log_level) # required to get level to apply.
    email_logger = logging.getLogger('atmosphere_emails')
    logger_initialize(email_logger)
    email_logger.setLevel(app_log_level)
