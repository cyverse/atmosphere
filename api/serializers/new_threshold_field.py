from rest_framework import serializers


class NewThresholdField(serializers.WritableField):

    def to_native(self, threshold_dict):
        return threshold_dict

    def field_from_native(self, data, files, field_name, into):
        value = data.get(field_name)
        if value is None:
            return
        memory = value.get('memory',0)
        disk = value.get('disk',0)
        machine_request = self.root.object
        machine_request.new_machine_memory_min = memory
        machine_request.new_machine_storage_min = disk
        into[field_name] = value