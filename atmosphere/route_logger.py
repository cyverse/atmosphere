from threepio import logger

class RouteLogger(object):
    """
    Use this to ensure tasks are being routed appropriately
    """
    def route_for_task(self, task, *args, **kwargs):
        logger.info("ROUTE: Creating a NEW route for Celery AsyncTask: %r %r %r" % (task, args, kwargs))
     
