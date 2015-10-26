from core.models import (
    BootScript, Identity, Instance,
    Provider, ProviderMachine, Project,
    Size, Volume)
from rest_framework import serializers
from api.v2.serializers.fields.base import ReprSlugRelatedField

class InstanceSerializer(serializers.ModelSerializer):
    identity = serializers.SlugRelatedField(source='created_by_identity', slug_field='uuid', queryset=Identity.objects.all())
    provider = serializers.SlugRelatedField(source='created_by_identity__provider', slug_field='uuid', queryset=Provider.objects.all())
    name = serializers.CharField()
    project = serializers.SlugRelatedField(source="projects", slug_field="uuid", queryset=Project.objects.all())
    scripts = serializers.SlugRelatedField(slug_field="uuid", many=True, required=False, queryset=BootScript.objects.all())
    #NOTE: These 'alias' point to the 'native IDs' NOT the db-UUID!
    #NOTE: either 'volume_alias' or 'machine_alias' is REQUIRED for a CREATE
    machine_alias = ReprSlugRelatedField(source="source", repr_slug_field="identifier", slug_field="instance_source__identifier", required=False, queryset=ProviderMachine.objects.all())
    volume_alias = ReprSlugRelatedField(source="source", repr_slug_field="identifier", slug_field="instance_source__identifier", required=False, queryset=Volume.objects.all())
    size_alias = serializers.SlugRelatedField(source="instancestatushistory_set.size", slug_field="alias", queryset=Size.objects.all())

    def __init__(self, *args, **kwargs):
        """
        As of DRF 3.2.4 This is the *ONLY* way to 'limit_choices_to' 
        or to dynamically assign a queryset based on the data passed to the serializer.
        See https://github.com/tomchristie/django-rest-framework/issues/1811
        AND https://github.com/tomchristie/django-rest-framework/issues/1985
        For a 'Future-Proof' solution.
        """
        # This is required to be passed in
        identity_uuid = kwargs['data'].get('identity')
        # These fields have querysets that are *dynamic* based on provider (uuid)
        provider_f = self.fields['provider']
        machine_f = self.fields['machine_alias']
        volume_f = self.fields['volume_alias']
        size_f = self.fields['size_alias']

        provider_f.queryset = provider_f.queryset.filter(identity__uuid=identity_uuid)
        if not provider_f.queryset:
            machine_f.queryset = machine_f.queryset.none()
            volume_f.queryset = volume_f.queryset.none()
            size_f.queryset = size_f.queryset.none()
        elif len(provider_f.queryset) > 1:
            raise Exception("Implementation Error -- Only ever expected one value here! Fix this line!")
        else:
            #ASSERT: Queryset is EXACTLY ONE value.
            provider_uuid = provider_f.queryset.first().uuid
            machine_f.queryset = machine_f.queryset.filter(instance_source__provider__uuid=provider_uuid)
            volume_f.queryset = volume_f.queryset.filter(instance_source__provider__uuid=provider_uuid)
            size_f.queryset = size_f.queryset.filter(provider__uuid=provider_uuid)
        super (InstanceSerializer, self).__init__(*args, **kwargs)

    class Meta:
        model = Instance
        fields = (
            'provider',
            'identity',
            'name',
            'project',
            'machine_alias',
            'volume_alias',
            'size_alias',
            'scripts',
        )

