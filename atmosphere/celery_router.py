from threepio import logger

#Ripped from asksol answer --See http://stackoverflow.com/questions/10707287/django-celery-routing-problems
class PredeclareRouter(object):
    setup = False

    def route_for_task(self, *args, **kwargs):
        if self.setup:
            return
        self.setup = True
        from celery import current_app
        from celery import VERSION as celery_version
        # will not connect anywhere when using the Django transport
        # because declarations happen in memory.
        with current_app.broker_connection() as conn:
            queues = current_app.amqp.queues
            channel = conn.default_channel
            if celery_version >= (2, 6):
                for queue in queues.itervalues():
                    queue(channel).declare()
            else:
                from kombu.common import entry_to_queue
                for name, opts in queues.iteritems():
                    entry_to_queue(name, **opts)(channel).declare()

class CloudRouter(PredeclareRouter):
    """
    This router will:
    * Log routes for tasks as they are added to the system
    """
    def route(self, options, task, args=(), kwargs={}):
        print "Route called"
        return

    def route_for_task(self, task, *args, **kwargs):
        super(CloudRouter, self).route_for_task(task, *args, **kwargs)
        the_route = self.prepare_route(task)
        if the_route:
            logger.info("ROUTE: Assigning Route %s for Celery AsyncTask: %r %r %r" % (the_route, task, args, kwargs))
        else:
            logger.info("ROUTE: Assigning Route Default for Celery AsyncTask: %r %r %r" % (task, args, kwargs))

        return the_route

    def prepare_route(self, task_name):
        if task_name in ["migrate_instance_task", "chromogenic.tasks.migrate_instance_task"]:
            return {"queue": "imaging", "routing_key": "imaging"}
        elif task_name in ["machine_imaging_task", "chromogenic.tasks.machine_imaging_task"]:
            return {"queue": "imaging", "routing_key": "imaging.execute"}
        elif task_name in ["freeze_instance_task", "service.tasks.machine.freeze_instance_task"]:
            return {"queue": "imaging", "routing_key": "imaging.prepare"}
        elif task_name in ["process_request", "service.tasks.machine.process_request"]:
            return {"queue": "imaging", "routing_key": "imaging.complete"}
        elif task_name in ["send_email", "service.tasks.email.send_email"]:
            return {"queue": "email", "routing_key": "email.sending"}
        elif task_name in ["_deploy_init_to", "service.tasks.driver._deploy_init_to"]:
            return {"queue": "ssh_deploy", "routing_key": "long.deployment"}
        elif task_name in ["wait_for_instance", "deploy_ready_test"]:
            return {"queue": "fast_deploy", "routing_key": "short.deployment"}
        else:
            logger.info("Could not place a routing key for TASK:%s"
                    % task_name)
            return {"queue": "default", "routing_key": "default"}
