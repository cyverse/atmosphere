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
