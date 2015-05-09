from core.models.application import ApplicationScore
from core.models.machine import ProviderMachine
from core.models import Tag
from core.models.instance_source import InstanceSource
from rest_framework import serializers
from .cleaned_identity_serializer import CleanedIdentitySerializer
from .license_serializer import LicenseSerializer
from .tag_related_field import TagRelatedField


class ProviderMachineSerializer(serializers.ModelSerializer):
    #R/O Fields first!
    alias = serializers.ReadOnlyField(source='instance_source.identifier')
    alias_hash = serializers.SerializerMethodField()
    created_by = serializers.CharField(
        read_only=True, source='application_version.application.created_by.username')
    created_by_identity = CleanedIdentitySerializer(
        source='instance_source.created_by_identity')
    icon = serializers.CharField(read_only=True, source='icon_url')
    private = serializers.CharField(
        read_only=True, source='application_version.application.private')
    architecture = serializers.CharField(read_only=True,
                                         source='esh_architecture')
    ownerid = serializers.CharField(read_only=True, source='esh_ownerid')
    state = serializers.CharField(read_only=True, source='esh_state')
    scores = serializers.SerializerMethodField()
    #Writeable fields
    name = serializers.CharField(source='application_version.application.name')
    # tags = serializers.CharField(source='application_version.application.tags.all')
    tags = TagRelatedField(slug_field='name', source='application_version.application.tags.all', many=True, queryset=Tag.objects.all())
    allow_imaging = serializers.BooleanField(source='application_version.allow_imaging', read_only=True)
    licenses = LicenseSerializer(source='licenses.all', many=True, read_only=True)
    description = serializers.CharField(source='application_version.application.description')
    start_date = serializers.ReadOnlyField(source='instance_source.start_date')
    end_date = serializers.ReadOnlyField(source='instance_source.end_date')
    featured = serializers.BooleanField(source='application_version.application.featured')
    identifier = serializers.ReadOnlyField(source="instance_source.identifier")
    version = serializers.CharField(source="application_version.name", read_only=True)

    def __init__(self, *args, **kwargs):
        self.request_user = kwargs.pop('request_user', None)
        super(ProviderMachineSerializer, self).__init__(*args, **kwargs)

    def get_alias_hash(self, pm):
        return pm.hash_alias()

    def get_scores(self, pm):
        app = pm.application_version.application
        scores = app.get_scores()
        update_dict = {
            "has_voted": False,
            "vote_cast": None}
        if not self.request_user:
            scores.update(update_dict)
            return scores
        last_vote = ApplicationScore.last_vote(app, self.request_user)
        if last_vote:
            update_dict["has_voted"] = True
            update_dict["vote_cast"] = last_vote.get_vote_name()
        scores.update(update_dict)
        return scores

    class Meta:
        model = ProviderMachine
        exclude = ('id', 'instance_source', 'licenses',)
