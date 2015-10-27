from core.models import (
    BootScript, Identity, Instance,
    Provider, ProviderMachine, Project,
    Size, Volume)
from rest_framework import serializers
from api.v2.serializers.fields.base import ReprSlugRelatedField

class InstanceSerializer(serializers.ModelSerializer):
    """
    This is a 'utility serializer' it should be used for preparing a v2 POST *ONLY*

    This serializer should *never* be returned to the user.
    instead, the core instance should be re-serialized into a 'details serializer'
    """
    identity = serializers.SlugRelatedField(source='created_by_identity', slug_field='uuid', queryset=Identity.objects.all())
    provider_uuid = serializers.SlugRelatedField(source='created_by_identity.provider', slug_field='uuid', read_only=True)
    name = serializers.CharField()
    project = serializers.SlugRelatedField(source="projects", slug_field="uuid", queryset=Project.objects.all())
    scripts = serializers.SlugRelatedField(slug_field="uuid", many=True, required=False, queryset=BootScript.objects.all())
    #NOTE: These 'alias' point to the 'cloud/native IDs' NOT the db-UUID!
    #NOTE: source_alias should belong to volume.identifier or providermachine.identifier
    source_alias = serializers.CharField(source="source__identifier")
    size_alias = serializers.SlugRelatedField(source="instancestatushistory_set.size", slug_field="alias", queryset=Size.objects.all())
    # Optional kwargs to be inluded
    deploy = serializers.BooleanField(default=True)
    extra = serializers.DictField(required=False)


    def __init__(self, *args, **kwargs):
        """
        As of DRF 3.2.4 This is the *ONLY* way to 'limit_choices_to' 
        or to dynamically assign a queryset based on the data passed to the serializer.
        See https://github.com/tomchristie/django-rest-framework/issues/1811
        AND https://github.com/tomchristie/django-rest-framework/issues/1985
        For a 'Future-Proof' solution.
        """
        # This is required to be passed in
        identity_uuid = kwargs.get('data',{}).get('identity')
        if not identity_uuid:
            super (InstanceSerializer, self).__init__(*args, **kwargs)
            return
        #request_user = self.context['request'].user
        # These fields have querysets that are *dynamic* based on provider (uuid)
        project_f = self.fields['project']
        provider_f = self.fields['provider_uuid']
        size_f = self.fields['size_alias']

        provider_queryset = Provider.objects.filter(identity__uuid=identity_uuid)
        if not provider_queryset:
            project_f.queryset = project_f.queryset.none()
            size_f.queryset = size_f.queryset.none()
        elif len(provider_queryset) > 1:
            raise Exception("Implementation Error -- Only ever expected one value here! Fix this line!")
        else:
            #ASSERT: Queryset is EXACTLY ONE value.
            provider_uuid = provider_queryset.first().uuid
            #project_f.queryset = project_f.queryset.filter(owner__user=request_user)
            size_f.queryset = size_f.queryset.filter(provider__uuid=provider_uuid)
        super (InstanceSerializer, self).__init__(*args, **kwargs)

    class Meta:
        model = Instance
        fields = (
            'provider_uuid',
            'identity',
            'name',
            'project',
            'size_alias',
            'source_alias',
            'scripts',
            'deploy',
            'extra',
        )

