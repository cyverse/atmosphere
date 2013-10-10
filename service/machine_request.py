from chromogenic.tasks import machine_imaging_task

def start_machine_imaging(machine_request, delay=False):
    """
    Builds a machine imaging task using the machine_request
    delay - If true, wait until task is completed before returning
    """
    machine_request.status = 'enqueued'
    provider = machine_request.parent_machine.provider
    provider_creds = provider.get_credentials()
    provider_admin = provider.get_admin_identity().get_credentials()
    provider_creds.update(provider_admin)

    migrate_creds = {}

    new_provider = machine_request.new_machine_provider
    if provider.id != new_provider.id:
        migrate_creds.update(new_provider.get_credentials())
        migrate_creds.update(new_provider.get_admin_identity().get_credentials())
        
    #TODO: Logic for if delay = True..
    machine_imaging_task.si(machine_request,
                            provider_creds,
                            migrate_creds).apply_async()
    machine_request.save()
#TODO:
# After request is finished:
# 
#set_machine_request_metadata(manager, machine_request, machine)
#process_machine_request(machine_request, new_image_id)
#send_image_request_email(machine_request.new_machine_owner,
#                         machine_request.new_machine,
#                         machine_request.new_machine_name)
#

def set_machine_request_metadata(manager, machine_request, machine):
    manager.driver.ex_set_image_metadata(machine, {'deployed':'True'})
    if machine_request.new_machine_description:
        metadata['description'] = machine_request.new_machine_description
    if machine_request.new_machine_tags:
        metadata['tags'] = machine_request.new_machine_tags
    logger.info("LC Driver:%s - Machine:%s - Metadata:%s" % (lc_driver,
            machine.id, metadata))
    lc_driver.ex_set_image_metadata(machine, metadata)
    return machine


