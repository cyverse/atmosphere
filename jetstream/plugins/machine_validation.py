from atmosphere.plugins.machine_validation import MachineValidationPlugin
from django.conf import settings
from threepio import logger


class JetstreamValidation(MachineValidationPlugin):
    """
    Represents the current strategy being used by Jetstream

    Default metadata_key is: `atmosphere_catalog`
    To set the metadata_key to a non-standard value,
    include `WHITELIST_METADATA_KEY = "new_metadata_key"` in `variables.ini`
    and re-configure.
    """
    def __init__(self, account_driver):
        metadata_key = getattr(settings, "WHITELIST_METADATA_KEY", "atmosphere_catalog")
        self.metadata_key = metadata_key

    def machine_is_valid(self, cloud_machine):
        """
        Given a cloud_machine (glance image)

        Return True if the machine should be included in Atmosphere's catalog
        Return False if the machine should be skipped

        In this plugin, a cloud_machine is skipped if:
        - metadata_key is not found in image metadata
        - image does not pass the 'sanity checks'
        """
        if not self._sanity_check_machine(cloud_machine):
            return False
        elif not self._contains_metadata(cloud_machine, self.metadata_key):
            logger.info("Skipping cloud machine %s - Missing metadata_key: %s", cloud_machine, self.metadata_key)
            return False
        return True
