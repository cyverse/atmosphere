from threepio import logger


def get_driver(driverCls, provider, identity, **provider_credentials):
    """
    Create a driver object from a class, provider and identity.
    """
    from rtwo import compute
    compute.initialize()
    if not provider_credentials:
        provider_credentials = provider.options
    driver = driverCls(provider, identity, **provider_credentials)
    if driver:
        return driver


def get_admin_driver(provider):
    """
    Create an admin driver for a given provider.
    """
    try:
        from api import get_esh_driver
        return get_esh_driver(provider.accountprovider_set.all()[0].identity)
    except:
        logger.info("Admin driver for provider %s not found." %
                    (provider.location))
        return None


class DriverManager(object):

    _instance = None

    def __new__(cls, *args, **kwargs):
        """
        Create a new instance if it doesnt exist already
        """
        if not cls._instance:
            cls._instance = super(DriverManager, cls).__new__(
                cls, *args, **kwargs)
            cls._instance.driver_map = {}
        return cls._instance

    def get_driver(self, core_identity):
        from api import get_esh_driver
        #No Cache model
        driver = get_esh_driver(core_identity)
        return driver
        #Cached model
        if not self.driver_map.get(core_identity):
            driver = get_esh_driver(core_identity)
            self.driver_map[core_identity] = driver
            logger.info("Driver created for identity %s : %s"
                        % (core_identity, driver))
            return driver
        driver = self.driver_map[core_identity]
        logger.info("Driver found for identity %s: %s"
                    % (core_identity, driver))
        return driver

    def release_all_drivers(self):
        """
        Sometimes we need to release the entire pool..
        """
        self.driver_map = {}

    def release_driver(self, core_identity):
        if self.driver_map.get(core_identity):
            del self.driver_map[core_identity]
