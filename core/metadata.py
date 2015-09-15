# -*- coding: utf-8 -*-
"""
Maintain objects metadata
"""

from threepio import logger


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
