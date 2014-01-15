from service.metadata import update_machine_metadata, _get_owner_identity

def write_app_data(esh_driver, provider_machine):
    """
    """
    #NOTES: 
    # Dep loop if raised any higher..
    # This function is temporary..
    from api import get_esh_driver
    account_providers = provider_machine.provider.accountprovider_set.all()
    if not account_providers:
        raise Exception("The driver of the account provider is required to"
                        " update image metadata")
    account_provider = account_providers[0].identity
    esh_driver = get_esh_driver(account_provider)
    esh_machine = esh_driver.get_machine(provider_machine.identifier)
    mach_data = {
        # Specific to the provider machine
        "application_version":str(provider_machine.version), 
        # Specific to the application
        "application_uuid":provider_machine.application.uuid,
        "application_name":provider_machine.application.name,
        "application_owner":provider_machine.application.created_by.username,
        "application_tags":json.dumps(
            [tag for tag in provider_machine.application.tags.all()]),
        "application_description":provider_machine.application.description,
    }
    return update_machine_metadata(esh_driver, esh_machine, mach_data)

def has_app_data(metadata):
    return all([metadata.has_key('application_%s' % key) for key in
                ["version", "uuid", "name", "owner", "tags", "description"]])

def get_app_data(metadata, provider_id):
    create_app_kwargs = {}
    for key,val in metadata.items():
        if key.startswith('application_'):
            create_app_kwargs[key.replace('application_','')] = val
    owner_name = create_app_kwargs["owner"]
    create_app_kwargs["owner"] = _get_owner_identity(owner_name, provider_id)
    return create_app_kwargs
