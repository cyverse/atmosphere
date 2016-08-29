from threepio import logger

# Ripped from asksol answer --See
# http://stackoverflow.com/questions/10707287/django-celery-routing-problems


class PredeclareRouter(object):
    setup = False

    def route_for_task(self, *args, **kwargs):
        if self.setup:
            return
        self.setup = True
        from celery import app as current_app
        # will not connect anywhere when using the Django transport
        # because declarations happen in memory.
        # Create queues on initialization
        with current_app.broker_connection() as conn:
            queues = current_app.amqp.queues
            channel = conn.default_channel
            for queue in queues.itervalues():
                queue(channel).declare()
DEPLOY_TASKS = [
    "_deploy_init_to", "service.tasks.driver._deploy_init_to",
    "deploy_ready_test", "service.tasks.driver.deploy_ready_test", 
    "check_process_task", "service.tasks.driver.check_process_task", 
]
EMAIL_TASKS = [
    "send_email", "core.tasks.email.send_email",
]
IMAGING_TASKS = [
    # Atmosphere specific
    "freeze_instance_task", "service.tasks.machine.freeze_instance_task",
    "process_request", "service.tasks.machine.process_request",
    "imaging_complete", "validate_new_image",
    # Chromogenic
    "migrate_instance_task", "chromogenic.tasks.migrate_instance_task",
    "machine_imaging_task", "chromogenic.tasks.machine_imaging_task",
    "chromogenic.tasks.migrate_instance_task",
    "chromogenic.tasks.machine_imaging_task",
    "service.tasks.machine.freeze_instance_task",
    "service.tasks.machine.process_request",

]
PERIODIC_TASKS = [
    "monitor_instances", "monitor_instances_for",
    "monitor_instance_allocations",
    "monitor_machines", "monitor_machines_for",
    "monitor_sizes", "monitor_sizes_for",
    "monitor_volumes", "monitor_volumes_for",
    "prune_machines", "prune_machines_for",
    "check_image_membership", "update_membership_for",
    "clear_empty_ips", "clear_empty_ips_for",
    "remove_empty_networks",
    "remove_empty_networks_for",
    "reset_provider_allocation",
    "monthly_allocation_reset",
    #JETSTREAM_SPECIFIC PERIODIC TASKS
    "report_allocations_to_tas",
    "update_snapshot",
    "monitor_jetstream_allocation_sources"
]
SHORT_TASKS = [
    "wait_for_instance",
]


class CloudRouter(PredeclareRouter):

    """
    This router will:
    * Log routes for tasks as they are added to the system
    """

    def route(self, options, task, args=(), kwargs={}):
        print "ROUTE() called: %s - %s - %s" % (task, args, kwargs)
        return

    def route_for_task(self, task, *args, **kwargs):
        super(CloudRouter, self).route_for_task(task, *args, **kwargs)
        the_route = self.prepare_route(task)
        if the_route:
            logger.info(
                "ROUTE: Assigning Route %s for Celery AsyncTask: %r %r %r" %
                (the_route, task, args, kwargs))
        else:
            logger.info(
                "ROUTE: Assigning Route Default for Celery AsyncTask: %r %r %r" %
                (task, args, kwargs))
        return the_route

    def prepare_route(self, task_name):
        if task_name in SHORT_TASKS:
            return {"queue": "fast_deploy", "routing_key": "short.deployment"}
        elif task_name in IMAGING_TASKS:
            return {"queue": "imaging", "routing_key": "imaging"}
        elif task_name in EMAIL_TASKS:
            return {"queue": "email", "routing_key": "email.sending"}
        elif task_name in PERIODIC_TASKS:
            return {"queue": "periodic", "routing_key": "periodic"}
        elif task_name in DEPLOY_TASKS:
            return {"queue": "ssh_deploy", "routing_key": "long.deployment"}
        else:
            logger.info("ROUTE: Could not place a routing key for TASK:%s"
                    % task_name)
            return {"queue": "default", "routing_key": "default"}
