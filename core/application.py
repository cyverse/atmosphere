import json

from core.metadata import update_machine_metadata, _get_owner_identity

from threepio import logger



def get_app_driver(provider_machine):
    from service.driver import get_admin_driver
    provider = provider_machine.provider
    esh_driver = get_admin_driver(provider)
    if not esh_driver:
        raise Exception("The driver of the account provider is required to"
                        " update image metadata")
    return esh_driver

def save_app_data(application):
    all_pms = application.providermachine_set.all()
    if not all_pms:
        return
    for provider_machine in all_pms:
        try:
            esh_driver = get_app_driver(provider_machine)
            write_app_data(esh_driver, provider_machine)
        except AttributeError:
            logging.exception("Error writing app data to %s."
                              "HINT: Does it still exist?"
                              % provider_machine)

def write_app_data(esh_driver, provider_machine):
    esh_driver = get_app_driver(provider_machine)
    esh_machine = esh_driver.get_machine(provider_machine.identifier)
    mach_data = {
        # Specific to the provider machine
        "application_version": str(provider_machine.version),
        # Specific to the application
        "application_uuid": provider_machine.application.uuid,
        "application_name": provider_machine.application.name,
        "application_owner": provider_machine.application.created_by.username,
        "application_tags": json.dumps(
            [tag.name for tag in provider_machine.application.tags.all()]),
        "application_description": provider_machine.application.description,
    }
    logger.info("Machine<%s> new app data: %s"
                % (provider_machine.identifier, mach_data))
    return update_machine_metadata(esh_driver, esh_machine, mach_data)


def clear_app_data(esh_driver, provider_machine):
    esh_driver = get_app_driver(provider_machine)
    esh_machine = esh_driver.get_machine(provider_machine.identifier)
    mach_data = {
        # Specific to the provider machine
        "application_version": "",
        # Specific to the application
        "application_uuid": "",
        "application_name": "",
        "application_owner": "",
        "application_tags": "",
        "application_description": "",
    }
    return update_machine_metadata(esh_driver, esh_machine, mach_data)


def has_app_data(metadata):
    return all([metadata.get('application_%s' % key) for key in
                ["version", "uuid", "name", "owner", "tags", "description"]])


def get_app_data(metadata, provider_id):
    create_app_kwargs = {}
    for key, val in metadata.items():
        if key.startswith('application_'):
            create_app_kwargs[key.replace('application_', '')] = val
    owner_name = create_app_kwargs["owner"]
    create_app_kwargs["owner"] = _get_owner_identity(owner_name, provider_id)
    create_app_kwargs["tags"] = json.loads(create_app_kwargs["tags"])
    return create_app_kwargs
