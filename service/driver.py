from threepio import logger


def get_hypervisor_statistics(admin_driver):
    if hasattr(admin_driver._connection, "ex_hypervisor_statistics"):
        return None
    all_instance_stats = admin_driver._connection.ex_hypervisor_statistics()
    all_instances = admin_driver.list_all_instances()
    for instance in all_instances:
        pass


def get_driver(driverCls, provider, identity, **provider_credentials):
    """
    Create a driver object from a class, provider and identity.
    """
    from rtwo import compute
    compute.initialize()
    if not provider_credentials:
        provider_credentials = provider.options
    driver = driverCls(provider, identity, **provider_credentials)
    if driver:
        return driver


def get_admin_driver(provider):
    """
    Create an admin driver for a given provider.
    """
    try:
        from api import get_esh_driver
        return get_esh_driver(provider.accountprovider_set.all()[0].identity)
    except:
        logger.info("Admin driver for provider %s not found." %
                    (provider.location))
        return None


def get_account_driver(provider):
    """
    Create an account driver for a given provider.
    """
    try:
        type_name = provider.get_type_name().lower()
        if 'openstack' in type_name:
            from service.accounts.openstack import AccountDriver as\
                    OSAccountDriver
            return OSAccountDriver(provider)
        elif 'eucalyptus' in type_name:
            from service.accounts.eucalyptus import AccountDriver as\
                    EucaAccountDriver
            return EucaAccountDriver(provider)
    except:
        logger.exception("Account driver for provider %s not found." %
                    (provider.location))
        return None
