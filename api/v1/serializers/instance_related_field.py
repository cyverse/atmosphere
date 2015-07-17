from core.models.instance import Instance
from rest_framework import serializers


class InstanceRelatedField(serializers.RelatedField):

    def to_native(self, instance_alias):
        instance = Instance.objects.get(provider_alias=instance_alias)
        return instance.provider_alias

    def field_from_native(self, data, files, field_name, into):
        value = data.get(field_name)
        if value is None:
            return
        try:
            into["instance"] = Instance.objects.get(provider_alias=value)
            into[field_name] = Instance.objects.get(
                provider_alias=value).provider_alias
        except Instance.DoesNotExist:
            into[field_name] = None
