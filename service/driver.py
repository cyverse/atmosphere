def get_driver(driverCls, provider, identity):
    """
    Create a driver object from a class, provider and identity.
    """
    from rtwo import compute
    compute.initialize()
    driver = driverCls(provider, identity)
    if driver:
        return driver
