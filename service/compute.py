"""
Atmosphere service compute.
"""

from atmosphere import settings
from atmosphere.logger import logger

from service.provider import AWSProvider, EucaProvider, OSProvider
from service.driver import EucaDriver, AWSDriver


def _initialize_provider(provider, driverCls, **kwargs):
    try:
        identity = provider.identityCls(provider, **kwargs)
        driver = driverCls(provider, identity)
        machs = driver.list_machines()
        logger.info("Caching %s machines for %s" % (len(machs), provider))
        driver.list_sizes()
    except Exception as e:
        logger.exception(e)


def _initialize_aws():
    if hasattr(settings, 'AWS_KEY') \
       and hasattr(settings, 'AWS_SECRET'):
        _initialize_provider(AWSProvider(),
                             AWSDriver,
                             key=settings.AWS_KEY,
                             secret=settings.AWS_SECRET,
                             user="admin")


def _initialize_euca():
    if hasattr(settings, 'EUCA_ADMIN_KEY') \
       and hasattr(settings, 'EUCA_ADMIN_SECRET'):
        _initialize_provider(EucaProvider(),
                             EucaDriver,
                             key=settings.EUCA_ADMIN_KEY,
                             secret=settings.EUCA_ADMIN_SECRET,
                             user="admin")


def initialize():
    """
    Initialize machines and sizes using an admin identity.

    NOTE: This is required to ensure Eucalyptus and AWS have valid information
    for sizes and machines.
    """
    _initialize_euca()
    _initialize_aws()

EucaProvider.set_meta()
AWSProvider.set_meta()
OSProvider.set_meta()
initialize()
