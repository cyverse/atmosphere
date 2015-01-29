from core.models.application import Application
from rest_framework import serializers
from .app_bookmark_field import AppBookmarkField
from .projects_field import ProjectsField
from .boot_script_serializer import BootScriptSerializer
from .get_context_user import get_context_user


class ApplicationSerializer(serializers.ModelSerializer):
    """
    """
    #Read-Only Fields
    uuid = serializers.CharField(read_only=True)
    icon = serializers.CharField(read_only=True, source='icon_url')
    created_by = serializers.SlugRelatedField(slug_field='username',
                                              source='created_by',
                                              read_only=True)
    #scores = serializers.Field(source='get_scores')
    uuid_hash = serializers.CharField(read_only=True, source='hash_uuid')
    #Writeable Fields
    name = serializers.CharField(source='name')
    tags = serializers.CharField(source='tags.all')
    description = serializers.CharField(source='description')
    start_date = serializers.CharField(source='start_date')
    end_date = serializers.CharField(source='end_date',
                                     required=False, read_only=True)
    private = serializers.BooleanField(source='private')
    featured = serializers.BooleanField(source='featured')
    machines = serializers.SerializerMethodField('get_machines')
    is_bookmarked = AppBookmarkField(source="bookmarks.all")
    threshold = serializers.RelatedField(read_only=True, source="threshold")
    projects = ProjectsField()
    scripts = BootScriptSerializer(source='scripts', many=True, required=False)

    def get_machines(self, application):
        machines = application._current_machines(request_user=self.request_user)
        return [{"start_date": pm.start_date,
                 "end_date": pm.end_date,
                 "alias": pm.identifier,
                 "version": pm.version,
                 "provider": pm.provider.uuid} for pm in machines]


    def __init__(self, *args, **kwargs):
        user = get_context_user(self, kwargs)
        self.request_user = user
        super(ApplicationSerializer, self).__init__(*args, **kwargs)

    class Meta:
        model = Application
        exclude = ("created_by_identity","id")