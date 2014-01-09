from threepio import logger

class DriverManager(object):

    _instance = None

    def __new__(cls, *args, **kwargs):
        """
        Create a new instance if it doesnt exist already
        """
        if not cls._instance:
            cls._instance = super(DriverManager, cls).__new__(cls, *args, **kwargs)
            cls._instance.driver_map = {}
        return cls._instance

    def get_driver(self, core_identity):
        from api import get_esh_driver
        if self.driver_map.get(core_identity):
            driver = self.driver_map[core_identity]
            logger.info("Driver reused: %s" % driver)
            return driver
        driver = get_esh_driver(core_identity)
        logger.info("Driver initialized: %s" % driver)
        self.driver_map[core_identity] = driver
        return driver

    def release_all_drivers(self):
        """
        Sometimes we need to release the entire pool..
        """
        self.driver_map = {}

    def release_driver(self, core_identity):
        if self.driver_map.get(core_identity):
            del self.driver_map[core_identity]
