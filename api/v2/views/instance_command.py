from rest_framework.response import Response
from api.v2.views.base import AuthViewSet
from rest_framework import status
from rest_framework import serializers
from api.v2.exceptions import failure_response
from threepio import logger
from core.models.instance import Instance
from api.v2.serializers.details.instance_command import InstanceCommandSerializer, POST_InstanceCommandSerializer, COMMANDS


class InstanceCommandViewSet(AuthViewSet):
    """
    The InstanceCommand viewset is part of a larger "Subspace 2.0" feature:

    Todo for full feature completion:
    - LIST: A list of commands (dynamically generated?) available for an instance.
    - CREATE: User is issuing a command from the list of command, validate accordingly and create necessary celery tasks/event hooks/etc. to start the process in motion.
    """
    serializer_class = InstanceCommandSerializer

    def list(self, request):
        serializer = InstanceCommandSerializer(COMMANDS, many=True)
        return Response(serializer.data)

    def create(self, request):
        request_data = request.data
        serializer = POST_InstanceCommandSerializer(
            data=request_data, context={'request': request})
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST)
        try:
            data = serializer.save()
            if data['status'] == 'success':
                data["message"] = "Successfully executed command."
                return Response(data, status=status.HTTP_201_CREATED)
            else:
                data["message"] = "Failed to execute command."
                return failure_response(
                    status.HTTP_409_CONFLICT, data)
        except Exception as exc:
            logger.exception(exc)
            return failure_response(
                status.HTTP_409_CONFLICT, exc.message)
        request_user = request.user
        request_data = request.data
        serializer = POST_InstanceCommandSerializer(
            data=request_data, context={'request': request})
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST)
        try:
            data = serializer.save()
            data["message"] = "Successfully executed command."
            return Response(data, status=status.HTTP_201_CREATED)
        except serializers.ValidationError as exc:
            return failure_response(
                status.HTTP_400_BAD_REQUEST,
                exc.message)
        except Exception as exc:
            return failure_response(
                status.HTTP_409_CONFLICT,
                exc.message)

    def _execute_command(self, request_user, request_data):
        self._validate_request(request_user, request_data)
        (run_command, instance, command_params) = self._prepare_command(request_user, request_data)
        try:
            results = run_command(instance, command_params)
            return results
        except Exception as exc:
            logger.exception("An error occurred while executing command:" + exc)
            raise

    def _prepare_command(self, request_user, request_data):
        if "command" not in request_data:
            return serializers.ValidationError(
                "command: required to run commands")
        if "instance_id" not in request_data:
            return serializers.ValidationError(
                "instance_id: required to run commands")

        instance_id = request_data.get("instance_id")
        instance = Instance.shared_with_user(request_user)\
            .filter(provider_alias=instance_id).first()
        if not instance:
            return serializers.ValidationError(
                "instance_id: Instance ID does not exist")
        command_name = request_data.get("command")
        command_params = request_data.get("params", {})
        command_type = type(command_params)
        if command_type != dict:
            return serializers.ValidationError(
                "command_params: Invalid type (%s), expected dict"
                % command_type)
        run_command = filter(
            _command for _command in COMMANDS
            if _command.name == command_name)
        if not run_command:
            raise serializers.ValidationError(
                "Command `%s` not found" % command_name)
        command_fn = run_command[0].handler
        return (command_fn, instance, command_params)

    def _validate_request(self, request_user, request_data):
        # user permission checking
        if not request_user.is_staff and not request_user.is_superuser:
            raise serializers.ValidationError(
                "BETA Feature: Non-staff users are not allowed to run commands"
            )
