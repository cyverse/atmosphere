from rest_framework import serializers


class NewThresholdField(serializers.Field):

    def to_representation(self, threshold_dict):
        return threshold_dict

    def to_internal_value(self, data):
        value = data.get('threshold')
        if value is None:
            return
        memory = value.get('memory', 0)
        disk = value.get('disk', 0)
        machine_request = self.root.object
        machine_request.new_machine_memory_min = memory
        machine_request.new_machine_storage_min = disk
        return {
            'memory': memory,
            'disk': disk
        }
