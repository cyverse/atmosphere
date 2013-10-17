import time

from celery.decorators import task
from service.machine_request import set_machine_request_metadata
from core.email import send_image_request_email
from core.models.machine_request import MachineRequest, process_machine_request

from service.deploy import freeze_instance, sync_instance
from service.tasks.driver import deploy_to
from threepio import logger

@task(name='process_request', ignore_result=False)
def process_request(new_image_id, machine_request_id):
    machine_request = MachineRequest.objects.get(id=machine_request_id)
    set_machine_request_metadata(machine_request, machine)
    process_machine_request(machine_request, new_image_id)
    send_image_request_email(machine_request.new_machine_owner,
                             machine_request.new_machine,
                             machine_request.new_machine_name)

@task(name='freeze_instance_task', ignore_result=False)
def freeze_instance_task(machine_request_id, instance_id):
    from api import get_esh_driver
    machine_request = MachineRequest.objects.get(id=machine_request_id)
    identity = machine_request.instance.created_by_identity
    driver = get_esh_driver(identity)
    kwargs = {}
    private_key = "/opt/dev/atmosphere/extras/ssh/id_rsa"
    kwargs.update({'ssh_key': private_key})
    kwargs.update({'timeout': 120})

    si_script = sync_instance()
    kwargs.update({'deploy': si_script})

    instance = driver.get_instance(instance_id)
    driver.deploy_to(instance, **kwargs)

    fi_script = freeze_instance()
    kwargs.update({'deploy': fi_script})
    deploy_to.delay(
        driver.__class__, driver.provider, driver.identity,
        instance.id, **kwargs)
    #Give it a head-start..
    time.sleep(1)
    return
