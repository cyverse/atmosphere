from core.models import (
    BootScript, Identity, Instance, InstanceSource,
    Provider, ProviderMachine, Project, UserAllocationSource,
    Size, Volume)
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from api.v2.serializers.fields.base import ReprSlugRelatedField

class InstanceSerializer(serializers.ModelSerializer):
    """
    This is a 'utility serializer' it should be used for preparing a v2 POST *ONLY*

    This serializer should *never* be returned to the user.
    instead, the core instance should be re-serialized into a 'details serializer'
    """
    identity = serializers.SlugRelatedField(
        source='created_by_identity', slug_field='uuid',
        queryset=Identity.objects.all())
    provider_uuid = serializers.SlugRelatedField(
        source='created_by_identity.provider', slug_field='uuid',
        read_only=True)
    uuid = serializers.CharField(source='provider_alias', read_only=True)
    name = serializers.CharField()
    project = serializers.SlugRelatedField(
        source="projects", slug_field="uuid", queryset=Project.objects.all(),
        required=False, allow_null=True)
    scripts = serializers.SlugRelatedField(
        slug_field="uuid", queryset=BootScript.objects.all(),
        many=True, required=False)
    #NOTE: These 'alias' point to the 'cloud/native IDs' NOT the db-UUID!
    #NOTE: source_alias should belong to volume.identifier or providermachine.identifier
    source_alias = serializers.SlugRelatedField(source="source", slug_field="identifier", queryset=InstanceSource.objects.all())
    size_alias = serializers.SlugRelatedField(source="instancestatushistory_set.size", slug_field="alias", queryset=Size.objects.all())
    # Optional kwargs to be inluded
    deploy = serializers.BooleanField(default=True)
    extra = serializers.DictField(required=False)
    # Note: When CyVerse uses the allocation_source, remove 'required=False'
    allocation_source_id = serializers.CharField(write_only=True, required=False)

    def to_internal_value(self, data):
        """
        Overwrite to force custom logic required before accepting data to launch an instance.
        1. check of identity prior to checking size_alias or source_alias
        NOTE: This is required because we have identical alias' on multiple providers, so we must first filter-down based on the identity requested for launching the instance.
        2. Check source_alias is either a Volume or a ProviderMachine before continuing.
        """

        identity_uuid = data.get('identity')
        if not identity_uuid:
            raise ValidationError({
                'identity': 'This field is required.'
            })
        request_user = self.context['request'].user

        size_queryset = self.fields['size_alias'].queryset
        allocation_source_queryset = UserAllocationSource.objects.filter(user=request_user)
        source_queryset = self.fields['source_alias'].queryset

        allocation_source_id = data.get('allocation_source_id')
        #NOTE: When CyVerse uses the allocation_source feature, remove 'and 'jetstream' in settings.INSTALLED_APPS'
        if not allocation_source_id and 'jetstream' in settings.INSTALLED_APPS:
            raise ValidationError({
                'allocation_source_id': 'This field is required.'
            })
        allocation_source = allocation_source_queryset.filter(allocation_source__source_id=allocation_source_id)
        if not allocation_source:
            raise ValidationError({
                'allocation_source_id': 'Value %s did not match a allocation_source.' % allocation_source_id
            })

        size_alias = data.get('size_alias')
        if not size_alias:
            raise ValidationError({
                'size_alias': 'This field is required.'
            })
        size = size_queryset.filter(alias=size_alias)
        if not size:
            raise ValidationError({
                'size_alias': 'Value %s did not match a Size.' % size_alias
            })

        source_alias = data.get('source_alias')
        if not source_alias:
            raise ValidationError({
                'source_alias': 'This field is required.'
            })
        source = InstanceSource.get_source(
            source_alias, queryset=source_queryset)
        if not source:
            raise ValidationError({
                'source_alias': 'Value %s did not match a ProviderMachine or Volume.' % source_alias
            })
        return super(InstanceSerializer, self).to_internal_value(data)

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
        source_f = self.fields['source_alias']
        provider_queryset = Provider.objects.filter(identity__uuid=identity_uuid)
        if not provider_queryset:
            project_f.queryset = project_f.queryset.none()
            size_f.queryset = size_f.queryset.none()
            source_f.queryset = source_f.queryset.none()
        elif len(provider_queryset) > 1:
            raise Exception("Implementation Error -- Only ever expected one value here! Fix this line!")
        else:
            #ASSERT: Queryset is EXACTLY ONE value.
            provider_f.queryset = provider_queryset
            provider_uuid = provider_queryset.first().uuid
            source_f.queryset = source_f.queryset.filter(provider__uuid=provider_uuid)
            size_f.queryset = size_f.queryset.filter(provider__uuid=provider_uuid)
        super (InstanceSerializer, self).__init__(*args, **kwargs)

    class Meta:
        model = Instance
        fields = (
            'uuid',
            'provider_uuid',
            'identity',
            'name',
            'project',
            'size_alias',
            'source_alias',
            'scripts',
            'deploy',
            'extra',
            'allocation_source_id'
        )

