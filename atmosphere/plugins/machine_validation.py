from django.conf import settings

from threepio import logger


class MachineValidationPlugin(object):
    def __init__(self, account_driver):
        self.account_driver = account_driver

    def machine_is_valid(self, cloud_machine):
        raise NotImplementedError(
            "Validation plugins must implement a machine_is_valid function "
            "that takes arguments: 'accounts', 'cloud_machine'")

    def _sanity_check_machine(self, cloud_machine):
        """
        The following sanity checks should be done on any image, before adding to
        the catalog:

        - Fail if image is None
        - Fail if image status is not 'active'
        - Fail if image is a 'snapshot'
        - Fail if image is a kernel or ramdisk
        """
        # Skip the machine if the owner was not the chromogenic image creator
        # (tenant name must match admin tenant name)
        # If that behavior changes, this snippet should be updated/removed.
        if not cloud_machine:
            return False
        elif not self._is_active(cloud_machine):
            return False
        elif self._is_kernel_or_ramdisk(cloud_machine):
            return False
        elif self._is_snapshot(cloud_machine):
            return False
        return True

    def _contains_metadata(self, cloud_machine, metadata_key):
        if not hasattr(cloud_machine, metadata_key):
            return False
        metadata_value = str(cloud_machine.get(metadata_key)).lower()
        if metadata_value in ['yes', 'true']:
            return True
        elif metadata_value in ['no', 'false']:
            return False
        else:
            logger.info("Encountered unexpected (Not-truthy) metadata_value for %s:%s", metadata_key, metadata_value)
            return False

    def _machine_authored_by_atmosphere(self, cloud_machine):
        project_id = cloud_machine.get('owner')
        owner_project = self.account_driver.get_project_by_id(project_id)
        if not owner_project:
            owner = cloud_machine.get('application_owner')
            owner_project = self.account_driver.get_project(owner)
        # Assumption: the atmosphere imaging author == the project_name set for the account_driver.
        atmo_author_project_name = self.account_driver.project_name
        if not owner_project:
            logger.info(
                "cloud machine %s - authored by project_id %s, not the Atmosphere author: %s",
                cloud_machine.id, project_id, atmo_author_project_name)
            return False
        elif owner_project.name != atmo_author_project_name:
            logger.info(
                "cloud machine %s - authored by Tenant %s, not the Atmosphere author: %s",
                cloud_machine.id, owner_project.name, atmo_author_project_name)
            return False
        return True

    def _is_kernel_or_ramdisk(self, cloud_machine):
        machine_type = cloud_machine.get('image_type', 'image')
        container_format = cloud_machine.get('container_format', '')
        disk_format = cloud_machine.get('disk_format', '')
        if (machine_type in ['ari', 'aki']) or (container_format in ['ari', 'aki']) or (disk_format in ['ari', 'aki']):
            logger.info("Skipping cloud machine %s - kernel/ramdisk found" % cloud_machine)
            return True
        return False

    def _is_active(self, cloud_machine):
        cloud_machine_status = cloud_machine.get('status','N/A')
        if cloud_machine_status == 'active':
            return True
        logger.info(
            "Skipping cloud machine %s, imaging status:'%s' != 'active'.", cloud_machine, cloud_machine_status)
        return False

    def _is_snapshot(self, cloud_machine):
        cloud_machine_name = cloud_machine.get('name','')
        if cloud_machine_name and cloud_machine_name.startswith("ChromoSnapShot"):
            logger.info("Skipping cloud machine %s - 'ChromoSnapShot' found" % cloud_machine)
        elif cloud_machine.get('image_type', 'image') == 'snapshot':
            logger.info("Skipping cloud machine %s - snapshot found" % cloud_machine)
        else:
            return False
        return True

    def _machine_in_same_domain(self, cloud_machine):
        """
        If we wanted to support 'domain-restrictions' *inside* of atmosphere,
        we could verify the domain of the image owner. If their domain does not match, skip.
        """
        project_id = cloud_machine.get('owner')
        owner_project = self.account_driver.get_project_by_id(project_id)
        if not owner_project:
            logger.info(
                "Skipping cloud machine %s, No owner listed.", cloud_machine)
            return False
        domain_id = owner_project.domain_id
        config_domain = self.account_driver.get_config('user', 'domain', 'default')
        owner_domain = self.account_driver.openstack_sdk.identity.get_domain(domain_id)
        account_domain = self.account_driver.openstack_sdk.identity.get_domain(config_domain)
        if owner_domain.id != account_domain.id:
            logger.info("Cloud machine %s - owner domain (%s) does not match %s",
                        cloud_machine, owner_domain, account_domain)
            return False
        return True


class BasicValidation(MachineValidationPlugin):
    """
    Represents the minimal set of checks required to include a new
    image into the catalog
    """
    def machine_is_valid(self, cloud_machine):
        """
        Given a cloud_machine (glance image)

        Return True if it passes the sanity checks.
        """
        return self._sanity_check_machine(cloud_machine)


class BlacklistValidation(MachineValidationPlugin):
    """
    Default blacklist metadata_key is: `atmo_image_exclude`
    To set the metadata_key to a non-standard value,
    include `BLACKLIST_METADATA_KEY = "new_metadata_key"` in `variables.ini`
    and re-configure.
    """
    def __init__(self, account_driver):
        metadata_key = getattr(settings, "BLACKLIST_METADATA_KEY", "atmo_image_exclude")
        self.blacklist_metadata_key = metadata_key
        super(BlacklistValidation, self).__init__(account_driver)

    def machine_is_valid(self, cloud_machine):
        """
        Given a cloud_machine (glance image)

        Return True if the machine should be included in Atmosphere's catalog
        Return False if the machine should be skipped

        In this plugin, a cloud_machine is skipped if:
        - image is not authored by the admin user (atmoadmin/admin)
        - 'atmo_image_exclude' is found in image metadata
        - Cloud machine does not pass the 'sanity checks'
        """
        if not self._sanity_check_machine(cloud_machine):
            return False
        elif self._contains_metadata(cloud_machine, self.blacklist_metadata_key):
            logger.info(
                "Skipping cloud machine %s "
                "- Includes '%s' metadata",
                cloud_machine, self.blacklist_metadata_key)
            return False
        return True


class WhitelistValidation(MachineValidationPlugin):
    """
    Default whitelist metadata_key is: `atmo_image_include`
    To set the metadata_key to a non-standard value,
    include `WHITELIST_METADATA_KEY = "new_metadata_key"` in `variables.ini`
    and re-configure.
    """
    def __init__(self, account_driver):
        metadata_key = getattr(settings, "WHITELIST_METADATA_KEY", "atmo_image_include")
        self.whitelist_metadata_key = metadata_key
        super(WhitelistValidation, self).__init__(account_driver)

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
        elif not self._contains_metadata(cloud_machine, self.whitelist_metadata_key):
            logger.info(
                "Skipping cloud machine %s -"
                " Missing whitelist metadata_key: %s",
                cloud_machine, self.whitelist_metadata_key)
            return False
        return True


class CyverseValidation(BlacklistValidation):
    """
    Cyverse validation strategy:
    - Only include images authored by the admin user
    - Exclude images if the 'blacklist_metadata_key' is found.

    Notes:
    - Default blacklist metadata_key is: `atmo_image_exclude`
    - To set the metadata_key to a non-standard value,
      include `BLACKLIST_METADATA_KEY = "new_metadata_key"` in `variables.ini`
      and re-configure.
    """

    def machine_is_valid(self, cloud_machine):
        """
        Given a cloud_machine (glance image)

        Return True if the machine should be included in Atmosphere's catalog
        Return False if the machine should be skipped

        In this plugin, a cloud_machine is skipped if:
        - image is not authored by the admin user (atmoadmin/admin)
        - 'atmo_image_exclude' is found in image metadata
        - Cloud machine does not pass the 'sanity checks'
        """
        if not self._sanity_check_machine(cloud_machine):
            return False
        elif self._contains_metadata(cloud_machine, self.blacklist_metadata_key):
            logger.info(
                "Skipping cloud machine %s "
                "- Includes '%s' metadata",
                cloud_machine, self.blacklist_metadata_key)
            return False
        elif not self._machine_authored_by_atmosphere(cloud_machine):
            logger.info(
                "Skipping cloud machine %s "
                "- Not authored by atmosphere",
                cloud_machine)
            return False
        return True
