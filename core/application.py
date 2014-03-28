import json

from core.metadata import update_machine_metadata, _get_owner_identity

from threepio import logger

def _fix_existing_machines():
    #NOTE: Run once on prod, then remove this function..
    from core.models import Provider, ProviderMachine, MachineRequest
    for pm in ProviderMachine.objects.filter(provider__in=Provider.get_active(type_name='openstack')):
        owner = pm.application.created_by
        if 'admin' not in owner.username:
            try:
                update_owner(pm, owner.username)
                print "Updated owner for %s" % owner
            except Exception, exc:
                print "Cannot update owner %s" % owner
                print "Exception = %s" % exc
    for mr in MachineRequest.objects.filter(new_machine__isnull=False, new_machine_provider__in=Provider.get_active(type_name='openstack')):
        owner = mr.new_machine_owner.username
        try:
            update_owner(mr.new_machine, owner)
            print "Updated owner for %s" % owner
        except Exception, exc:
            print "Cannot update owner %s" % owner
            print "Exception = %s" % exc


def update_owner(provider_machine, tenant_name):
    #TODO: If we switch from user-group model this will have to do some
    # lookup from username on provider to select specific tenant for
    # the _os_update portion..
    _db_update_owner(provider_machine.application, tenant_name)
    _os_update_owner(provider_machine, tenant_name)

def _db_update_owner(application, username):
    from core.models.user import AtmosphereUser
    application.created_by = AtmosphereUser.objects.get(username=username)
    application.save()


def _os_update_owner(provider_machine, tenant_name):
    from core.models import Provider
    from service.driver import get_admin_driver
    provider = provider_machine.provider
    if provider not in Provider.get_active(type_name='openstack'):
        raise Exception("An active openstack provider is required to"
                        " update image owner")
    esh_driver = get_admin_driver(provider)
    if not esh_driver:
        raise Exception("The account driver of Provider %s is required to"
                        " update image metadata" % provider)
    esh_machine = esh_driver.get_machine(provider_machine.identifier)
    if not esh_machine:
        raise Exception("Machine with ID  %s not found"
                        % provider_machine.identifier)
    tenant_id = _tenant_name_to_id(provider_machine.provider, tenant_name)
    update_machine_metadata(esh_driver, esh_machine,
                            {"owner": tenant_id,
                             "application_owner": tenant_name})


def get_app_driver(provider_machine):
    from service.driver import get_admin_driver
    provider = provider_machine.provider
    esh_driver = get_admin_driver(provider)
    if not esh_driver:
        raise Exception("The driver of the account provider is required to"
                        " update image metadata")
    return esh_driver

def _tenant_name_to_id(provider, tenant_name):
    from service.accounts.openstack import AccountDriver as OSAccountDriver
    if provider not in Provider.get_active(type_name='openstack'):
        raise Exception("An active openstack provider is required to"
                        " update image owner")
    accounts = OSAccountDriver(provider)
    if not accounts:
        raise Exception("The account driver of Provider %s is required to"
                        " update image metadata" % provider)
    tenant = accounts.get_project(tenant_name)
    if not tenant:
        raise Exception("Tenant named %s not found" % tenant_name)
    return tenant.id

def save_app_data(application):
    all_pms = application.providermachine_set.all()
    if not all_pms:
        return
    for provider_machine in all_pms:
        try:
            write_app_data(provider_machine)
        except AttributeError:
            logging.exception("Error writing app data to %s."
                              "HINT: Does it still exist?"
                              % provider_machine)

def write_app_data(provider_machine, **extras):
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
    mach_data.update(extras)
    logger.info("Machine<%s> new app data: %s"
                % (provider_machine.identifier, mach_data))
    return update_machine_metadata(esh_driver, esh_machine, mach_data)


def clear_app_data(provider_machine):
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
