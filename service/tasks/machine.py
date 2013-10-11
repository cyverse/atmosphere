from celery.decorators import task
from service.machine_request import set_machine_request_metadata
from core.email import send_image_request_email
from core.models.machine_request import MachineRequest, process_machine_request


@task(name='process_request', ignore_result=False)
def process_request(new_image_id, machine_request_id):
    machine_request = MachineRequest.objects.get(id=machine_request_id)
    set_machine_request_metadata(machine_request, machine)
    process_machine_request(machine_request, new_image_id)
    send_image_request_email(machine_request.new_machine_owner,
                             machine_request.new_machine,
                             machine_request.new_machine_name)
