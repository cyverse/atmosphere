import django
try:
    #FIXME: Find a way to make tasks 'visible' without abusing the __init__ files
    import service.tasks.accounts
    import service.tasks.monitoring
    import service.tasks.driver
    import service.tasks.volume
    import service.tasks.machine
    import service.tasks.snapshot
    import service.tasks.admin
    import chromogenic.tasks
except django.core.exceptions.AppRegistryNotReady:
    #logger.info("Tasks will not load until app is ready")
    print ("Tasks will not load until app is ready",)
    pass
