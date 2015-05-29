"""
Atmosphere service machine rest api.

"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from threepio import logger


from api import failure_response
from api.permissions import ApiAuthRequired
from api.serializers import MachineRequestSerializer
from core.models.machine_request import share_with_admins, share_with_self
from core.models.machine_request import MachineRequest as CoreMachineRequest
from core.models import Provider
from web.emails import requestImaging
from service.tasks.machine import start_machine_imaging
from service.instance import _permission_to_act
from service.exceptions import ActionNotAllowed

import copy
import re


class MachineRequestList(APIView):
    """
    This is the user portal for machine requests
    Here they can view all the machine requests they made
    as well as e-mail the admins to approve a machine request
    """

    permission_classes = (ApiAuthRequired,)
    
    def get(self, request, provider_uuid, identity_uuid):
        """
        """
        all_user_reqs = CoreMachineRequest.objects.filter(
            new_machine_owner=request.user)
        serialized_data = MachineRequestSerializer(all_user_reqs, many=True).data
        response = Response(serialized_data)
        return response

    def post(self, request, provider_uuid, identity_uuid):
        """
        Sends an e-mail to the admins to start
        the create_image process.
        """
        try:
            return self._create_image(request, provider_uuid, identity_uuid)
        except ActionNotAllowed:
            return failure_response(
                status.HTTP_409_CONFLICT,
                "Machine Imaging has been "
                "explicitly disabled on this provider.")
        except Exception, exc:
            return failure_response(
                status.HTTP_400_BAD_REQUEST, exc.message)

    def _create_image(self, request, provider_uuid, identity_uuid):
        _permission_to_act(identity_uuid, "Imaging")
        #request.DATA is r/o
        #Copy allows for editing
        data = copy.deepcopy(request.DATA)
        data.update({'owner': data.get('created_for', request.user.username)})
        if data.get('vis','public') != 'public':
            user_list  = re.split(', | |\n', data.get('shared_with',""))
            share_with_admins(user_list, data.get('provider'))
            share_with_self(user_list, request.user.username)
            user_list = [user for user in user_list if user] # Skips blanks
            #TODO: Remove duplicates as well..
            data['shared_with'] = user_list
        logger.info(data)
        serializer = MachineRequestSerializer(data=data)
        if serializer.is_valid():
            #Add parent machine to request
            instance = serializer.validated_data['instance']
            if instance.source.is_machine():
                serializer.validated_data['parent_machine'] = instance\
                        .source.providermachine
            elif instance.source.is_volume():
                raise Exception(
                        "Instance of booted volume can NOT be imaged."
                        "Contact your Administrator for more information.")
            else:
                raise Exception(
                        "Instance source type cannot be determined."
                        "Contact your Administrator for more information.")
            #NOTE: THIS IS A HACK -- While we enforce all images to go to iPlant Cloud - Tucson.
            # THIS CODE SHOULD BE REMOVED 
            try:
                tucson_provider = Provider.objects.get(location='iPlant Cloud - Tucson')
                if serializer.validated_data['new_machine_provider'] != tucson_provider:
                    raise Exception(
                       "Only the iPlant Cloud - Tucson Provider can create images."
                       " Please change your 'Cloud for Deployment'")
            except Provider.DoesNotExist:
                pass
            machine_request = serializer.save()
            #Object now has an ID for links..
            active_provider = machine_request.active_provider()
            auto_approve = active_provider.auto_imaging
            requestImaging(request, machine_request.id,
                           auto_approve=auto_approve)
            if auto_approve:
                start_machine_imaging(machine_request)
            return Response(serializer.data,
                            status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors,
                            status=status.HTTP_400_BAD_REQUEST)



class MachineRequest(APIView):
    """
    MachineRequests are available to allow users
    to request that their instance be permanantly saved,
    so that it can be re-launched as a new Application at a later date.
    Upon request, these applications can be made Public, Private, or available
    to a specific set of users.
    """
    permission_classes = (ApiAuthRequired,)
    
    def get(self, request, provider_uuid, identity_uuid, machine_request_id):
        """
        Authentication Required, get information about a previous request.
        """
        try:
            machine_request = CoreMachineRequest.objects.get(
                id=machine_request_id)
        except CoreMachineRequest.DoesNotExist:
            return Response('No machine request with id %s'
                            % machine_request_id,
                            status=status.HTTP_404_NOT_FOUND)

        serialized_data = MachineRequestSerializer(machine_request).data
        response = Response(serialized_data)
        return response

    def patch(self, request, provider_uuid, identity_uuid, machine_request_id):
        """Authentication Required, update information on a pending request.
        """
        #Meta data changes in 'pending' are OK
        #Status change 'pending' --> 'cancel' are OK
        data = request.DATA
        try:
            machine_request = CoreMachineRequest.objects.get(
                id=machine_request_id)
        except CoreMachineRequest.DoesNotExist:
            return Response('No machine request with id %s'
                            % machine_request_id,
                            status=status.HTTP_404_NOT_FOUND)

        serializer = MachineRequestSerializer(machine_request,
                                              data=data, partial=True)
        if serializer.is_valid():
            machine_request = serializer.object
            if machine_request.status == 'approve':
                start_machine_imaging(machine_request)
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, provider_uuid, identity_uuid, machine_request_id):
        """Authentication Required, update information on a pending request.
        """
        #Meta data changes in 'pending' are OK
        #Status change 'pending' --> 'cancel' are OK
        data = request.DATA
        try:
            machine_request = CoreMachineRequest.objects.get(
                id=machine_request_id)
        except CoreMachineRequest.DoesNotExist:
            return Response('No machine request with id %s'
                            % machine_request_id,
                            status=status.HTTP_404_NOT_FOUND)

        serializer = MachineRequestSerializer(machine_request,
                                              data=data, partial=True)
        if serializer.is_valid():
            #Only run task if status is 'approve'
            machine_request = serializer.object
            if machine_request.status == 'approve':
                start_machine_imaging(machine_request)
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
