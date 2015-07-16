from core.models.provider import AccountProvider, Provider
from core.models.identity import Identity
from threepio import logger


def _get_machine_metadata(esh_driver, esh_machine):
    if not hasattr(esh_driver._connection, 'ex_get_image_metadata'):
        # NOTE: This can get chatty, only uncomment for debugging
        # Breakout for drivers (Eucalyptus) that don't support metadata
        # logger.debug("EshDriver %s does not have function 'ex_get_image_metadata'"
        #            % esh_driver._connection.__class__)
        return {}
    try:
        metadata = esh_driver._connection.ex_get_image_metadata(esh_machine)
        return metadata
    except Exception:
        logger.exception(
            'Warning: Metadata could not be retrieved for: %s' %
            esh_machine)
        return {}


def update_machine_metadata(esh_driver, esh_machine, data={}):
    """
    NOTE: This will NOT WORK for TAGS until openstack
    allows JSONArrays as values for metadata!
    """
    if not hasattr(esh_driver._connection, 'ex_set_image_metadata'):
        logger.info(
            "EshDriver %s does not have function 'ex_set_image_metadata'" %
            esh_driver._connection.__class__)
        return {}
    try:
        # Possible metadata that could be in 'data'
        #  * application uuid
        #  * application name
        #  * specific machine version
        # TAGS must be converted from list --> String
        logger.info("New metadata:%s" % data)
        meta_response = esh_driver._connection.ex_set_image_metadata(
            esh_machine,
            data)
        esh_machine.invalidate_machine_cache(esh_driver.provider, esh_machine)
        return meta_response
    except Exception as e:
        logger.exception("Error updating machine metadata")
        if 'incapable of performing the request' in e.message:
            return {}
        else:
            raise


def _get_admin_owner(provider_uuid):
    admin = AccountProvider.objects.filter(provider__uuid=provider_uuid)
    if not admin:
        logger.warn("AccountProvider could not be found for provider %s."
                    " AccountProviders are necessary to claim ownership "
                    " for identities that do not yet exist in the DB."
                    % Provider.objects.get(uuid=provider_uuid))
        return None
    return admin[0].identity


def _get_owner_identity(owner_name, provider_uuid):
    original_owner = Identity.objects.filter(
        provider__uuid=provider_uuid,
        created_by__username=owner_name)
    if original_owner:
        owner_identity = original_owner[0]
    else:
        admin = _get_admin_owner(provider_uuid)
        if not admin:
            raise Exception(
                "Original owner %s does not exist in DB and no "
                "AccountProvider could be found to assume ownership."
                "Select an Identity to be the AccountProvider or "
                "create an Identity for %s."
                % (owner_name, owner_name))
        owner_identity = admin
    return owner_identity
