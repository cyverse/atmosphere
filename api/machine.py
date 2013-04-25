"""
Atmosphere service machine rest api.

"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from atmosphere.logger import logger

from authentication.decorators import api_auth_token_required

from api import prepareDriver, failureJSON
from api.serializers import ProviderMachineSerializer
from core.models.machine import convertEshMachine, update_machine_metadata


class MachineList(APIView):
    """
    Represents:
        A Manager of Machine
        Calls to the Machine Class
    TODO: POST when we have programmatic image creation/snapshots
    """

    @api_auth_token_required
    def get(self, request, provider_id, identity_id):
        """
        Using provider and identity, getlist of machines
        TODO: Cache this request
        """
        esh_driver = prepareDriver(request, identity_id)
        esh_machine_list = esh_driver.list_machines()
        esh_machine_list = esh_driver.filter_machines(
            esh_machine_list,
            black_list=['eki-', 'eri-'])
        core_machine_list = [convertEshMachine(esh_driver, mach, provider_id)
                             for mach in esh_machine_list]
        serialized_data = ProviderMachineSerializer(core_machine_list).data
        response = Response(serialized_data)
        return response


class Machine(APIView):
    """
    Represents:
        Calls to modify the single machine
    TODO: DELETE when we allow owners to 'end-date' their machine..
    """

    @api_auth_token_required
    def get(self, request, provider_id, identity_id, machine_id):
        """
        Lookup the machine information
        (Lookup using the given provider/identity)
        Update on server (If applicable)
        """
        esh_driver = prepareDriver(request, identity_id)
        eshMachine = esh_driver.get_machine(machine_id)
        coreMachine = convertEshMachine(esh_driver, eshMachine, provider_id)
        serialized_data = ProviderMachineSerializer(coreMachine).data
        response = Response(serialized_data)
        return response

    @api_auth_token_required
    def patch(self, request, provider_id, identity_id, machine_id):
        """
        TODO: Determine who is allowed to edit machines besides
            coreMachine.owner
        """
        user = request.user
        data = request.DATA
        esh_driver = prepareDriver(request, identity_id)
        esh_machine = esh_driver.get_machine(machine_id)
        coreMachine = convertEshMachine(esh_driver, esh_machine, provider_id)

        if not user.is_staff and user is not coreMachine.machine.created_by:
            logger.warn('%s is Non-staff/non-owner trying to update a machine'
                        % (user.username))
            errorObj = failureJSON([{
                'code': 401,
                'message':
                'Only Staff and the machine Owner '
                + 'are allowed to change machine info.'}])
            return Response(errorObj, status=status.HTTP_401_UNAUTHORIZED)

        coreMachine.machine.update(request.DATA)
        serializer = ProviderMachineSerializer(coreMachine,
                                               data=data, partial=True)
        if serializer.is_valid():
            logger.info('metadata = %s' % data)
            update_machine_metadata(esh_driver, esh_machine, data)
            serializer.save()
            logger.info(serializer.data)
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @api_auth_token_required
    def put(self, request, provider_id, identity_id, machine_id):
        """
        TODO: Determine who is allowed to edit machines besides
            coreMachine.owner
        """
        user = request.user
        data = request.DATA
        esh_driver = prepareDriver(request, identity_id)
        esh_machine = esh_driver.get_machine(machine_id)
        coreMachine = convertEshMachine(esh_driver, esh_machine, provider_id)

        if not user.is_staff and user is not coreMachine.machine.created_by:
            logger.warn('Non-staff/non-owner trying to update a machine')
            errorObj = failureJSON([{
                'code': 401,
                'message':
                'Only Staff and the machine Owner '
                + 'are allowed to change machine info.'}])
            return Response(errorObj, status=status.HTTP_401_UNAUTHORIZED)
        coreMachine.machine.update(data)
        serializer = ProviderMachineSerializer(coreMachine,
                                               data=data, partial=True)
        if serializer.is_valid():
            logger.info('metadata = %s' % data)
            update_machine_metadata(esh_driver, esh_machine, data)
            serializer.save()
            logger.info(serializer.data)
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
