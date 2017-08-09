from rest_framework import serializers
from core.models import Instance
from threepio import logger


class InstanceCommand:

    def __init__(self, name, desc, action, validate):
        self.name = name
        self.desc = desc
        self.action = action
        self.validate = validate


# list of commands available

COMMANDS = [
    # TODO: Include a viable list of instance commands
    # Example: 'add_guacamole', 'add_vncserver', 'restart_vncserver', ...
    # Any Idempotent and often-requested command
    # that we can let users access in a self-service fashion...
]


class POST_InstanceCommandSerializer(serializers.Serializer):
    command = serializers.CharField(max_length=256, write_only=True)
    instance_id = serializers.CharField(write_only=True)
    params = serializers.JSONField(write_only=True)
    results = serializers.JSONField(read_only=True)

    def _get_request_user(self):
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            return request.user
        user = self.context.get('user')
        return user

    def validate_command(self, value):
        valid_command = [c for c in COMMANDS if c.name == value]
        if not valid_command:
            raise serializers.ValidationError(
                "Command %s does not exist" % value)
        return valid_command[0]

    def validate_instance_id(self, value):
        request_user = self._get_request_user()
        instance = Instance.shared_with_user(
            request_user,
            is_leader=True).filter(
            provider_alias=value).first()
        if not instance:
            raise serializers.ValidationError(
                "Instance ID %s does not exist" % value)
        return instance

    def validate(self, data):
        validated_data = data.copy()
        params = data.get('params')
        command = data.get('command')
        if hasattr(command, 'validate'):
            try:
                command.validate(params)
            except Exception as exc:
                raise serializers.ValidationError(
                    "Error validating command: %s" % exc)
        validated_data['command'] = command
        return validated_data

    def create(self, validated_data):
        command = validated_data['command']
        instance = validated_data['instance_id']
        params = validated_data['params']
        try:
            results = command.action(instance, params)
            return {
                "status": "success",
                "results": results
            }
        except Exception as exc:
            logger.exception(exc)
            return {
                "status": "error",
                "error": str(exc)
            }

    class Meta:
        fields = ('instance_id', 'command', 'params', 'results')


class InstanceCommandSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(max_length=256)
    desc = serializers.CharField()

    class Meta:
        fields = ('id', 'name', 'desc')
