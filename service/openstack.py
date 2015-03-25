import pytz

from django.utils.timezone import datetime

from threepio import logger

from core.models import Provider, Identity
from service.driver import get_account_driver

def glance_write_machine(provider_machine):
    """
    Using the provider_machine in the DB, save information to the Cloud.
    """
    base_source = provider_machine.instance_source
    base_app = provider_machine.application
    identifier = base_source.identifier
    g_image = glance_image_for(provider_uuid, identifier)
    if not g_image:
        return
    #Do any updating that makes sense... Name.
    g_image.update(name=base_app.name)

def glance_update_machine(new_machine):
    """
    The glance API contains MOAR information about the image then
    a call to 'list_machines()' on the OpenStack (Compute/Nova) Driver.

    This method will call glance and update any/all available information.
    """
    base_source = new_machine.instance_source

    provider_uuid = base_source.provider.uuid
    identifier = base_source.identifier
    new_app = new_machine.application
    g_image = glance_image_for(provider_uuid, identifier)
    owner = glance_image_owner(provider_uuid, identifier)
    if owner:
        base_source.created_by = owner.created_by
        base_source.created_by_identity = owner
    # If glance image, we can also infer some about the application
    if g_image:
        logger.debug("Found glance image for %s" % new_machine)
        # Never set private=False if it's set True in the DB.
        if g_image.is_public is False:
            new_app.private = True

        g_end_date = glance_timestamp(g_image.deleted_at)
        g_start_date = glance_timestamp(g_image.created_at)
        if new_app.first_machine() is new_machine:
            logger.debug("Glance image represents App:%s" % new_app)
            new_app.created_by = owner.created_by
            new_app.created_by_identity = owner
            new_app.start_date = g_start_date
            new_app.end_date = g_end_date
        new_app.save()
        base_source.start_date = g_start_date
        base_source.end_date = g_end_date
    base_source.save()
    new_machine.save()


def glance_image_for(provider_uuid, identifier):
    try:
        prov = Provider.objects.get(uuid=provider_uuid)
        accounts = get_account_driver(prov)
        glance_image = accounts.get_image(identifier)
    except Exception as e:
        logger.exception(e)
        glance_image = None
    return glance_image


def glance_image_owner(provider_uuid, identifier):
    try:
        prov = Provider.objects.get(uuid=provider_uuid)
        accounts = get_account_driver(prov)
        glance_image = accounts.get_image(identifier)
        project = accounts.user_manager.get_project_by_id(glance_image.owner)
        image_owner = Identity.objects.get(
            provider__uuid=provider_uuid,
            created_by__username=project.name)
    except Exception as e:
        logger.exception(e)
        image_owner = None
    return image_owner


def glance_timestamp(iso_8601_stamp):
    if not iso_8601_stamp:
        return None
    try:
        datetime_obj = datetime.strptime(iso_8601_stamp, '%Y-%m-%dT%H:%M:%S.%f')
    except ValueError:
        try:
            datetime_obj = datetime.strptime(iso_8601_stamp, '%Y-%m-%dT%H:%M:%S')
        except ValueError:
            raise ValueError("Expected ISO8601 Timestamp in Format: YYYY-MM-DDTHH:MM:SS[.sssss]")
    # All Dates are UTC relative
    datetime_obj = datetime_obj.replace(tzinfo=pytz.utc)
    return datetime_obj
