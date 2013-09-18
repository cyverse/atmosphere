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
        
    machine_imaging_task.si(machine_request,
                            provider_creds,
                            migrate_creds).apply_async()
    machine_request.save()

