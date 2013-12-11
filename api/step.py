"""
Atmosphere api step.
"""
from rest_framework.views import APIView
from rest_framework.response import Response

from authentication.decorators import api_auth_token_required

from core.models.step import Step as CoreStep

from api.serializers import StepSerializer

from api import prepare_driver


class StepList(APIView):
    """
    List all steps for an identity.
    """
    @api_auth_token_required
    def get(self, request, provider_id, identity_id):
        """
        Using provider and identity, getlist of machines
        TODO: Cache this request
        """
        user = request.user
        esh_driver = prepare_driver(request, identity_id)
        serialized_data = []
        step_list = [s for s in CoreStep.objects.filter(created_by_identity__id=identity_id)]
        #        esh_size_list = esh_driver.list_sizes()
        #        core_size_list = [convert_esh_size(size, provider_id, user)
        #                          for size in esh_size_list]
        serialized_data = StepSerializer(step_list, many=True).data
        response = Response(serialized_data)
        return response


class Step(APIView):
    """
    View a details on a step.
    """
    @api_auth_token_required
    def get(self, request, provider_id, identity_id, step_id):
        """
        Lookup the size information (Lookup using the given provider/identity)
        Update on server DB (If applicable)
        """
        user = request.user
        esh_driver = prepare_driver(request, identity_id)
        esh_size = []
        serialized_data = []
#        esh_size = esh_driver.get_size(size_id)
#        core_size = convert_esh_size(esh_size, provider_id, user)
#        serialized_data = ProviderSizeSerializer(core_size).data
        response = Response(serialized_data)
        return response



            # elif 'step' == action:
            #     #TODO: Get script input (deploy)
            #     deploy_script = build_script(str(action_params.get('script')),
            #                                  action_params.get('script_name'))
            #     deploy_params = {'deploy':deploy_script,
            #                      'timeout':120,
            #                      'ssh_key':
            #                      '/opt/dev/atmosphere/extras/ssh/id_rsa'}
            #     success = esh_driver.deploy_to(esh_instance, **deploy_params)
            #     result_obj = {'success':success,
            #                   'stdout': deploy_script.stdout,
            #                   'stderr': deploy_script.stderr,
            #                   'exit_code': deploy_script.exit_status}
            #     #TODO: Return script output, error, & RetCode
