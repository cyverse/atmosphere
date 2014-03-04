"""
Atmosphere api step.
"""
from uuid import uuid1

from django.utils import timezone

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

from threepio import logger

from authentication.decorators import api_auth_token_required

from core.models.flow import Flow as CoreFlow
from core.models.identity import Identity as CoreIdentity
from core.models.instance import Instance as CoreInstance
from core.models.step import Step as CoreStep

from api.serializers import StepSerializer

from api import failure_response


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
        step_list = [s for s in CoreStep.objects.filter(
            created_by_identity__id=identity_id)]
        serialized_data = StepSerializer(step_list, many=True).data
        return Response(serialized_data)

    @api_auth_token_required
    def post(self, request, provider_id, identity_id):
        """
        Create a new step.
        """
        data = request.DATA.copy()
        valid, messages = validate_post(data)
        if not valid:
            return failure_response(
                status.HTTP_400_BAD_REQUEST,
                messages)
        if data.get("instance_alias"):
            instance = CoreInstance.objects.get(
                provider_alias=data["instance_alias"])
        else:
            instance = None
        if data.get("flow_alias"):
            flow = CoreFlow.objects.get(alias=data["flow_alias"])
        else:
            flow = None
        identity = CoreIdentity.objects.get(id=identity_id)
        step = CoreStep(alias=uuid1(),
                        name=data["name"],
                        script=data["script"],
                        instance=instance,
                        flow=flow,
                        created_by=request.user,
                        created_by_identity=identity)

        serializer = StepSerializer(step, data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return failure_response(
            status.HTTP_400_BAD_REQUEST,
            serializer.errors)


class Step(APIView):
    """
    View a details of a step.
    """
    @api_auth_token_required
    def get(self, request, provider_id, identity_id, step_id):
        """
        Get details of a specific step.
        """
        serialized_data = []
        try:
            step = fetch_step(identity_id, step_id)
        except CoreStep.DoesNotExist:
            return step_not_found(step_id)
        if not step:
            return step_not_found(step_id)
        serialized_data = StepSerializer(step).data
        return Response(serialized_data)

    @api_auth_token_required
    def put(self, request, provider_id, identity_id, step_id):
        """
        Update a specific step.

        NOTE: This may not affect an active step.
        """
        user = request.user
        serialized_data = []
        data = request.DATA.copy()
        try:
            step = fetch_step(identity_id, step_id)
        except CoreStep.DoesNotExist:
            return step_not_found(step_id)
        if not step:
            return step_not_found(step_id)
        if not user.is_staff and user != step.created_by:
            return failure_response(
                status.HTTP_400_BAD_REQUEST,
                "Only the step creator can update %s step." % step_id)
        required_fields(data, step)
        serializer = StepSerializer(step, data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return failure_response(
            status.HTTP_400_BAD_REQUEST,
            serializer.errors)


    @api_auth_token_required
    def delete(self, request, provider_id, identity_id, step_id):
        """
        Delete a specific step.

        NOTE: This may not affect an active step.
        """
        user = request.user
        serialized_data = []
        data = request.DATA.copy()
        try:
            step = fetch_step(identity_id, step_id)
        except CoreStep.DoesNotExist:
            return step_not_found(step_id)
        if not step:
            return step_not_found(step_id)
        if not user.is_staff and user != step.created_by:
            return failure_response(
                status.HTTP_400_BAD_REQUEST,
                "Only the step creator can delete %s step." %
                step_id)
        required_fields(data, step)
        step.end_date = timezone.now()
        serializer = StepSerializer(step, data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return failure_response(
            status.HTTP_400_BAD_REQUEST,
            serializer.errors)


def required_fields(data, step):
    """
    Required fields so DRF will allow put and deletes.
    """
    if not data.get("name"):
        data["name"] = step.name
    if not data.get("instance_alias"):
        data["instance_alias"] = step.instance.provider_alias
    if not data.get("script"):
        data["script"] = step.script


def fetch_step(identity_id, step_id):
    """
    Get a specific step core model object from the database.

    NOTE: We use alias not the actual step id. Database IDs are an
    implementation detail.
    """
    return CoreStep.objects.get(alias=step_id,
                                created_by_identity__id=identity_id)


def step_not_found(step_id):
    return failure_response(
        status.HTTP_404_NOT_FOUND,
        'Step %s was not found.' % step_id)


def validate_post(data):
    """
    Returns a 2-tuple. The first value is a boolean on whether
    the data is valid. The second value is a list of validation
    error messages.
    """
    valid = True
    messages = []
    for field in ("alias", "end_date"):
        if data.get(field):
            valid = False
            messages.append("Step POST may not contain %s." % field)
    return (valid, messages)
